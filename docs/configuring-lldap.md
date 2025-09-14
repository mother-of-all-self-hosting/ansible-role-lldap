<!--
SPDX-FileCopyrightText: 2020 - 2024 MDAD project contributors
SPDX-FileCopyrightText: 2020 - 2025 Slavi Pantaleev
SPDX-FileCopyrightText: 2020 Aaron Raimist
SPDX-FileCopyrightText: 2020 Chris van Dijk
SPDX-FileCopyrightText: 2020 Dominik Zajac
SPDX-FileCopyrightText: 2020 Mickaël Cornière
SPDX-FileCopyrightText: 2022 François Darveau
SPDX-FileCopyrightText: 2022 Julian Foad
SPDX-FileCopyrightText: 2022 Warren Bailey
SPDX-FileCopyrightText: 2023 - 2024 MASH project contributors
SPDX-FileCopyrightText: 2023 Antonis Christofides
SPDX-FileCopyrightText: 2023 Felix Stupp
SPDX-FileCopyrightText: 2023 Gergely Horváth
SPDX-FileCopyrightText: 2023 Pierre 'McFly' Marty
SPDX-FileCopyrightText: 2024 - 2025 Suguru Hirahara
SPDX-FileCopyrightText: 2024 Philipp Homann

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Setting up LLDAP

This is an [Ansible](https://www.ansible.com/) role which installs [LLDAP](https://github.com/lldap/lldap/) to run as a [Docker](https://www.docker.com/) container wrapped in a systemd service.

LLDAP is a lightweight authentication server that provides an opinionated, simplified LDAP interface for authentication.

See the project's [documentation](https://github.com/lldap/lldap/blob/main/README.md) to learn what LLDAP does and why it might be useful to you.

## Prerequisites

To run a LLDAP instance it is necessary to prepare a database. You can use a [SQLite](https://www.sqlite.org/), [Postgres](https://www.postgresql.org/), or [MySQL](https://www.mysql.com/) compatible database server. By default it is configured to use SQLite.

If you are looking for Ansible roles for a Postgres or MySQL compatible server, you can check out [ansible-role-postgres](https://github.com/mother-of-all-self-hosting/ansible-role-postgres) and [ansible-role-mariadb](https://github.com/mother-of-all-self-hosting/ansible-role-mariadb), both of which are maintained by the [Mother-of-All-Self-Hosting (MASH)](https://github.com/mother-of-all-self-hosting) team.

## Adjusting the playbook configuration

To enable LLDAP with this role, add the following configuration to your `vars.yml` file.

**Note**: the path should be something like `inventory/host_vars/mash.example.com/vars.yml` if you use the [MASH Ansible playbook](https://github.com/mother-of-all-self-hosting/mash-playbook).

```yaml
########################################################################
#                                                                      #
# lldap                                                                #
#                                                                      #
########################################################################

lldap_enabled: true

########################################################################
#                                                                      #
# /lldap                                                               #
#                                                                      #
########################################################################
```

### Set the hostname

To enable LLDAP you need to set the hostname as well. To do so, add the following configuration to your `vars.yml` file. Make sure to replace `example.com` with your own value.

```yaml
lldap_hostname: "example.com"
```

After adjusting the hostname, make sure to adjust your DNS records to point the domain to your server.

**Note**: hosting LLDAP under a subpath (by configuring the `lldap_path_prefix` variable) does not seem to be possible due to LLDAP's technical limitations.

### Set random strings

You also need to set random strings for a JWT secret and key seed. To do so, add the following configuration to your `vars.yml` file. The values can be generated with `pwgen -s 64 1` or in another way.

```yaml
lldap_environment_variables_lldap_jwt_secret: RANDOM_STRING_HERE

lldap_environment_variables_lldap_key_seed: RANDOM_STRING_HERE
```

### Specify the username and password for the initial admin user

It is necessary to create an initial user with admin privileges by adding the following configuration to your `vars.yml` file:

```yaml
lldap_environment_variables_lldap_ldap_user_dn: ADMIN_USER_USERNAME_HERE

lldap_environment_variables_lldap_ldap_user_pass: ADMIN_USER_PASSWORD_HERE
```

The password is used both for the LDAP bind and for the administration interface.

>[!NOTE]
> Changing those values does not update them once the user is created. The password can be updated on the LLDAP's UI. If you lost it, you can set `force_ldap_user_pass_reset` to `true` on `lldap_config.docker_template.toml` inside the mounted data directory in order to force a reset of the admin password to the value specified to `lldap_environment_variables_lldap_ldap_user_pass`.

### Specify database (optional)

You can specify a database used by LLDAP. By default it is configured to use SQLite, and the SQLite database is stored in the directory specified with `lldap_data_path`.

To use Postgres, add the following configuration to your `vars.yml` file:

```yaml
lldap_database_type: postgres
```

Set `mysql` to use a MySQL compatible database.

For other settings, check variables such as `lldap_database_postgres_*` and `lldap_database_mysql_*` on [`defaults/main.yml`](../defaults/main.yml).

### Configure LDAP / LLDAPS port (optional)

LLDAP uses the port 3890 for LDAP and port 6360 for LDAPS (LDAP over HTTPS), respectively.

By default they are not exposed to the internet as the LLDAP's container can be accessed by other containers via the internal network, which they connect to. It is also [not recommended](https://github.com/lldap/lldap/blob/main/docs/install.md#with-docker) to expose the LDAP port.

If you wish to expose the LDAPS port, add the following configuration to your `vars.yml` file and adjust the port as you see fit.

```yaml
lldap_container_ldaps_host_bind_port: 6360
```

### Configure the mailer (optional)

You can configure a SMTP mailer to enable it for sending password reset emails.

To configure it, add the following configuration to your `vars.yml` file as below (adapt to your needs):

```yaml
# Set to `true` if mailer is enabled
lldap_environment_variables_smtp_enabled: true

# Set the hostname of the SMTP server
lldap_environment_variables_smtp_host: ""

# Set the port number of the SMTP server
lldap_environment_variables_smtp_port: 587

# Set the username for the SMTP server
lldap_environment_variables_smtp_user: ""

# Set the password for the SMTP server
lldap_environment_variables_smtp_password: ""

# Set the email address that emails will be sent from
lldap_environment_variables_smtp_from: ""

# Set the email address to be specified to the reply-to header
lldap_environment_variables_smtp_to: ""

# Set `TLS` or `STARTTLS` to enable encrypted connection with the SMTP server
# Valid values: NONE, STARTTLS, TLS
lldap_environment_variables_smtp_encryption: NONE
```

⚠️ **Note**: without setting an authentication method such as DKIM, SPF, and DMARC for your hostname, emails are most likely to be quarantined as spam at recipient's mail servers. If you have set up a mail server with the [MASH project's exim-relay Ansible role](https://github.com/mother-of-all-self-hosting/ansible-role-exim-relay), you can enable DKIM signing with it. Refer [its documentation](https://github.com/mother-of-all-self-hosting/ansible-role-exim-relay/blob/main/docs/configuring-exim-relay.md#enable-dkim-support-optional) for details.

### Extending the configuration

There are some additional things you may wish to configure about the component.

Take a look at:

- [`defaults/main.yml`](../defaults/main.yml) for some variables that you can customize via your `vars.yml` file. You can override settings (even those that don't have dedicated playbook variables) using the `lldap_environment_variables_additional_variables` variable

See [the official documentation](https://github.com/lldap/lldap/blob/main/lldap_config.docker_template.toml) for a complete list of LLDAP's config options that you could put in `lldap_environment_variables_additional_variables`.

## Installing

After configuring the playbook, run the installation command of your playbook as below:

```sh
ansible-playbook -i inventory/hosts setup.yml --tags=setup-all,start
```

If you use the MASH playbook, the shortcut commands with the [`just` program](https://github.com/mother-of-all-self-hosting/mash-playbook/blob/main/docs/just.md) are also available: `just install-all` or `just setup-all`

## Usage

After running the command for installation, LLDAP becomes available at the specified hostname like `https://example.com`.

To get started, open the URL with a web browser, and log in to the instance with the administrator account. You can create additional users (admin-privileged or not) after that via the web frontend. See [this section](https://github.com/lldap/lldap/blob/main/README.md#usage) on the documentation for details about usage, including a recommended architecture.

For a command line interface, a third party client [LLDAP-CLI](https://github.com/Zepmann/lldap-cli) is available.

## Troubleshooting

### Check the service's logs

You can find the logs in [systemd-journald](https://www.freedesktop.org/software/systemd/man/systemd-journald.service.html) by logging in to the server with SSH and running `journalctl -fu lldap` (or how you/your playbook named the service, e.g. `mash-lldap`).

#### Increase logging verbosity

If you want to increase the verbosity, add the following configuration to your `vars.yml` file:

```yaml
lldap_environment_variables_lldap_verbose: true
```
