<!--
SPDX-FileCopyrightText: 2018-2025 Slavi Pantaleev
SPDX-FileCopyrightText: 2019-2022 Aaron Raimist
SPDX-FileCopyrightText: 2019-2023 MDAD project contributors
SPDX-FileCopyrightText: 2023 QEDeD
SPDX-FileCopyrightText: 2024 Fabio Bonelli
SPDX-FileCopyrightText: 2024 Nikita Chernyi
SPDX-FileCopyrightText: 2024-2026 Suguru Hirahara
SPDX-FileCopyrightText: 2026 spatterlight

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Molecule Testing

This role supports [Molecule](https://docs.ansible.com/projects/molecule/), an Ansible testing framework designed for developing and testing Ansible collections, playbooks, and roles.

## Prerequisites

To utilize Molecule you need to prepare several requirements:

- **x86** computer running one of these operating systems that make use of [systemd](https://systemd.io/):
  - **Archlinux**
  - **CentOS**, **Rocky Linux**, **AlmaLinux**, or possibly other RHEL alternatives (although your mileage may vary)
  - **Debian** (10/Buster or newer)
  - **Ubuntu** (18.04 or newer, although [20.04 may be problematic](https://github.com/mother-of-all-self-hosting/mash-playbook/blob/main/docs/ansible.md#supported-ansible-versions) if you run the Ansible playbook on it)
- `root` access on the computer which Molecule runs against
- [Ansible](http://ansible.com/) program
- [Python](https://www.python.org/)
  - Most distributions install Python by default, but some don't (e.g. Ubuntu 18.04) and require manual installation (something like `apt-get install python3`)
- [Docker](https://www.docker.com)
  - Access to Docker UNIX socket (`/var/run/docker.sock`) is required by default

## Installation

To set up the environment for using Molecule, run the command below on the terminal:

```bash
python3 -m venv ./molecule/venv
source ./molecule/venv/bin/activate
pip3 install -r ./molecule/requirements.txt
```

## Scenarios

Currently these testing scenarios are available:

### `default`

Tests a standard LLDAP installation, storing its data in SQLite.

### `mariadb`

Tests a standard LLDAP installation with the MariaDB database.

### `postgres`

Tests a standard LLDAP installation with the Postgres database.

## What the scenarios check

LLDAP has two surfaces that both have to work, and that have to work against the same data: an LDAP server on port 3890 and a web/GraphQL API on port 17170. A systemd service that is `active` proves neither of them, so every scenario runs the checks in [`resources/tasks/verify_lldap.yml`](./resources/tasks/verify_lldap.yml):

- a **real LDAP bind** on port 3890, spoken over a raw socket by [`resources/ldap_probe.py`](./resources/ldap_probe.py), which encodes LDAP's BER messages by hand and needs nothing but python3. The admin credentials this role configured must bind successfully, and — asked first, as a negative control — a wrong password must be refused with result code 49 (`invalidCredentials`)
- the bind DN is built from a base DN the scenario deliberately sets to something other than the role's default, so a successful bind also proves the role passed that value through to the server
- the GraphQL API must **refuse an unauthenticated caller** with a 401, and must accept the admin's JWT
- a user is **created over GraphQL and then searched for over LDAP**. Both halves matter: LDAP is asked for that user before it is created (it must not be there) and after (it must be, at exactly the expected DN). This is what makes the two ports one service instead of two processes that happen to be listening
- the running container is asked which version it is (`lldap --version` reports what was compiled in, not the tag it was pulled under) and it must be the version `defaults/main.yml` asks for
- the **database backend** is asked directly for the user that was created over GraphQL — SQLite, MariaDB or Postgres, depending on the scenario. The two server-backed scenarios additionally assert that no SQLite database was written, so that a silent fallback cannot pass

## Running

By default it is configured to run the scenarios on Ubuntu 26.04.

```bash
molecule test --scenario-name default
```

You can utilize other distributions by setting one to the `MOLECULE_DISTRO` environment variable:

```bash
# Ubuntu 24.04
MOLECULE_DISTRO=ubuntu2404 molecule test --scenario-name default

# Debian 13
MOLECULE_DISTRO=debian13 molecule test --scenario-name default

# Debian 12
MOLECULE_DISTRO=debian12 molecule test --scenario-name default
```
