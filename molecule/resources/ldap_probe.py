#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Slavi Pantaleev
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Speaks LDAP to an LLDAP server over a raw socket and reports what it saw.

Usage:
    ldap_probe.py <host> <port> <bind_dn> <bind_password>
                  [<search_base> <search_attribute> <search_value>]

Prints a single JSON object on stdout and always exits 0 when it managed to
talk to the server, so that the caller can assert on the result code rather
than on the exit status. A rejected bind is a result, not an error.

The point of speaking the protocol by hand is that nothing else in the test
can produce these bytes. An HTTP request to LLDAP's web interface, or a
"the systemd service is active" check, would still pass against a server whose
LDAP listener never came up or whose credentials do not work; a BindResponse
with resultCode 0 on port 3890 cannot.

Only python3's standard library is used, so this runs on any host the Molecule
scenarios target without installing an LDAP client.
"""

import json
import socket
import sys

# The subset of BER that LDAP (RFC 4511) needs for a bind and a search.
TAG_INTEGER = 0x02
TAG_OCTET_STRING = 0x04
TAG_ENUMERATED = 0x0A
TAG_SEQUENCE = 0x30
TAG_BIND_REQUEST = 0x60  # [APPLICATION 0]
TAG_BIND_RESPONSE = 0x61  # [APPLICATION 1]
TAG_SEARCH_REQUEST = 0x63  # [APPLICATION 3]
TAG_SEARCH_RESULT_ENTRY = 0x64  # [APPLICATION 4]
TAG_SEARCH_RESULT_DONE = 0x65  # [APPLICATION 5]
TAG_SIMPLE_AUTH = 0x80  # [CONTEXT 0], primitive
TAG_FILTER_EQUALITY = 0xA3  # [CONTEXT 3], constructed

SCOPE_WHOLE_SUBTREE = 2
DEREF_NEVER = 0


def encode_length(length):
    if length < 0x80:
        return bytes([length])
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(encoded)]) + encoded


def encode_tlv(tag, value):
    return bytes([tag]) + encode_length(len(value)) + value


def encode_integer(value):
    length = (value.bit_length() // 8) + 1
    return encode_tlv(TAG_INTEGER, value.to_bytes(length, "big", signed=True))


def encode_enumerated(value):
    return encode_tlv(TAG_ENUMERATED, bytes([value]))


def encode_boolean(value):
    return encode_tlv(0x01, b"\xff" if value else b"\x00")


def encode_string(value):
    return encode_tlv(TAG_OCTET_STRING, value.encode("utf-8"))


def decode_tlv(data, offset):
    """Returns (tag, value_bytes, offset_just_past_this_element)."""
    tag = data[offset]
    length = data[offset + 1]
    offset += 2
    if length & 0x80:
        length_of_length = length & 0x7F
        length = int.from_bytes(data[offset:offset + length_of_length], "big")
        offset += length_of_length
    return tag, data[offset:offset + length], offset + length


def read_message(connection, buffer):
    """Reads one complete LDAPMessage, returning (message_bytes, leftover)."""
    while True:
        if len(buffer) >= 2:
            try:
                _, value, end = decode_tlv(buffer, 0)
            except IndexError:
                value = None
            else:
                if len(buffer) >= end:
                    return buffer[:end], buffer[end:]
                del value
        chunk = connection.recv(65536)
        if not chunk:
            raise EOFError("the server closed the connection mid-message")
        buffer += chunk


def bind_request(message_id, bind_dn, password):
    body = (
        encode_integer(3)
        + encode_string(bind_dn)
        + encode_tlv(TAG_SIMPLE_AUTH, password.encode("utf-8"))
    )
    return encode_tlv(TAG_SEQUENCE, encode_integer(message_id) + encode_tlv(TAG_BIND_REQUEST, body))


def search_request(message_id, base, attribute, value):
    body = (
        encode_string(base)
        + encode_enumerated(SCOPE_WHOLE_SUBTREE)
        + encode_enumerated(DEREF_NEVER)
        + encode_integer(0)  # sizeLimit
        + encode_integer(30)  # timeLimit
        + encode_boolean(False)  # typesOnly
        + encode_tlv(TAG_FILTER_EQUALITY, encode_string(attribute) + encode_string(value))
        + encode_tlv(TAG_SEQUENCE, encode_string("dn"))
    )
    return encode_tlv(TAG_SEQUENCE, encode_integer(message_id) + encode_tlv(TAG_SEARCH_REQUEST, body))


def protocol_op(message):
    """Returns (tag, value_bytes) of the protocolOp inside an LDAPMessage."""
    _, envelope, _ = decode_tlv(message, 0)
    _, _, after_message_id = decode_tlv(envelope, 0)
    tag, value, _ = decode_tlv(envelope, after_message_id)
    return tag, value


def result_of(operation_body):
    """Reads the LDAPResult prefix (resultCode, matchedDN, diagnosticMessage)."""
    _, result_code, offset = decode_tlv(operation_body, 0)
    _, _matched_dn, offset = decode_tlv(operation_body, offset)
    _, diagnostic, _ = decode_tlv(operation_body, offset)
    return int.from_bytes(result_code, "big"), diagnostic.decode("utf-8", "replace")


def main():
    arguments = sys.argv[1:]
    if len(arguments) not in (4, 7):
        print(__doc__, file=sys.stderr)
        return 2

    host, port, bind_dn, bind_password = arguments[:4]
    report = {}

    connection = socket.create_connection((host, int(port)), timeout=30)
    connection.settimeout(30)
    try:
        connection.sendall(bind_request(1, bind_dn, bind_password))
        message, buffer = read_message(connection, b"")
        tag, body = protocol_op(message)
        if tag != TAG_BIND_RESPONSE:
            raise ValueError("expected a BindResponse, got protocolOp tag 0x%02x" % tag)
        report["bind_result_code"], report["bind_diagnostic"] = result_of(body)

        if len(arguments) == 7:
            search_base, search_attribute, search_value = arguments[4:]
            report["entries"] = []
            report["search_result_code"] = None
            if report["bind_result_code"] == 0:
                connection.sendall(search_request(2, search_base, search_attribute, search_value))
                while True:
                    message, buffer = read_message(connection, buffer)
                    tag, body = protocol_op(message)
                    if tag == TAG_SEARCH_RESULT_ENTRY:
                        _, object_name, _ = decode_tlv(body, 0)
                        report["entries"].append(object_name.decode("utf-8", "replace"))
                    elif tag == TAG_SEARCH_RESULT_DONE:
                        report["search_result_code"], report["search_diagnostic"] = result_of(body)
                        break
    finally:
        connection.close()

    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
