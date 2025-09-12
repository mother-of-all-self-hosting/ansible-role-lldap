<!--
SPDX-FileCopyrightText: 2020 - 2024 MDAD project contributors
SPDX-FileCopyrightText: 2020 - 2024 Slavi Pantaleev
SPDX-FileCopyrightText: 2020 Aaron Raimist
SPDX-FileCopyrightText: 2020 Chris van Dijk
SPDX-FileCopyrightText: 2020 Dominik Zajac
SPDX-FileCopyrightText: 2020 Mickaël Cornière
SPDX-FileCopyrightText: 2022 François Darveau
SPDX-FileCopyrightText: 2022 Julian Foad
SPDX-FileCopyrightText: 2022 Warren Bailey
SPDX-FileCopyrightText: 2023 Antonis Christofides
SPDX-FileCopyrightText: 2023 Felix Stupp
SPDX-FileCopyrightText: 2023 Pierre 'McFly' Marty
SPDX-FileCopyrightText: 2024 - 2025 Suguru Hirahara

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Setting up Kutt

This is an [Ansible](https://www.ansible.com/) role which installs [Kutt](https://kutt.it/) to run as a [Docker](https://www.docker.com/) container wrapped in a systemd service.

Kutt is a modern URL shortener with support for custom domains with functions like statistics and user management.

See the project's [documentation](https://github.com/thedevs-network/kutt/blob/main/README.md) to learn what Kutt does and why it might be useful to you.

## Prerequisites

To run a Kutt instance it is necessary to prepare a database. You can use a [SQLite](https://www.sqlite.org/), [Postgres](https://www.postgresql.org/), or [MySQL](https://www.mysql.com/) compatible database server. By default it is configured to use SQLite.

If you are looking for Ansible roles for a Postgres or MySQL compatible server, you can check out [ansible-role-postgres](https://github.com/mother-of-all-self-hosting/ansible-role-postgres) and [ansible-role-mariadb](https://github.com/mother-of-all-self-hosting/ansible-role-mariadb), both of which are maintained by the [Mother-of-All-Self-Hosting (MASH)](https://github.com/mother-of-all-self-hosting) team.

## Adjusting the playbook configuration

To enable Kutt with this role, add the following configuration to your `vars.yml` file.

**Note**: the path should be something like `inventory/host_vars/mash.example.com/vars.yml` if you use the [MASH Ansible playbook](https://github.com/mother-of-all-self-hosting/mash-playbook).

```yaml
########################################################################
#                                                                      #
# kutt                                                                 #
#                                                                      #
########################################################################

kutt_enabled: true

########################################################################
#                                                                      #
# /kutt                                                                #
#                                                                      #
########################################################################
```

### Set the hostname

To enable Kutt you need to set the hostname as well. To do so, add the following configuration to your `vars.yml` file. Make sure to replace `example.com` with your own value.

```yaml
kutt_hostname: "example.com"
```

After adjusting the hostname, make sure to adjust your DNS records to point the domain to your server.

**Note**: hosting Kutt under a subpath (by configuring the `kutt_path_prefix` variable) does not seem to be possible due to Kutt's technical limitations.

### Set a random string for signing authentication tokens

You also need to set a random string for signing authentication tokens. To do so, add the following configuration to your `vars.yml` file. The value can be generated with `pwgen -s 64 1` or in another way.

```yaml
kutt_environment_variables_jwt_secret: YOUR_SECRET_KEY_HERE
```

### Specify database (optional)

You can specify a database used by Kutt. By default it is configured to use SQLite, and the SQLite database is stored in the directory specified with `kutt_data_path`.

To use `pg` (node-postgres), a PostgreSQL client for Node.js, add the following configuration to your `vars.yml` file:

```yaml
kutt_database_type: pg
```

Set `mysql2` to use a MySQL compatible database via [MySQL2](https://sidorares.github.io/node-mysql2/docs), a MySQL client for Node.js.

>[!NOTE]
> It is possible to use `pg-native` for Postgres and `sqlite3` for SQlite. As they are not installed by default, you'll need to install them with `npm` beforehand.

For other settings, check variables such as `kutt_database_postgres_*` and `kutt_database_mysql_*` on [`defaults/main.yml`](../defaults/main.yml).

### Configure a Redis server for caching (optional)

Also, you can optionally enable a [Redis](https://redis.io/) server for managing cache.

If you are looking for an Ansible role for Redis, you can check out [ansible-role-redis](https://github.com/mother-of-all-self-hosting/ansible-role-redis) maintained by the [Mother-of-All-Self-Hosting (MASH)](https://github.com/mother-of-all-self-hosting) team. The roles for [KeyDB](https://keydb.dev/) ([ansible-role-keydb](https://github.com/mother-of-all-self-hosting/ansible-role-keydb)) and [Valkey](https://valkey.io/) ([ansible-role-valkey](https://github.com/mother-of-all-self-hosting/ansible-role-valkey)) are available as well.

To enable Redis for Kutt, add the following configuration to your `vars.yml` file, so that the Kutt instance will connect to the server:

```yaml
kutt_redis_hostname: YOUR_REDIS_SERVER_HOSTNAME_HERE
kutt_redis_port: 6379
kutt_redis_password: YOUR_REDIS_SERVER_PASSWORD_HERE
kutt_redis_database: 0
```

Make sure to replace `YOUR_REDIS_SERVER_HOSTNAME_HERE` and `YOUR_REDIS_SERVER_PASSWORD_HERE` with your own values.

### Configure the mailer (optional)

You can configure a SMTP mailer to enable it for for signing up, verifying or changing email address, resetting password, and sending reports.

To configure it, add the following configuration to your `vars.yml` file as below (adapt to your needs):

```yaml
# Set to `true` if mailer is enabled
kutt_environment_variables_smtp_enabled: true

# Set the hostname of the SMTP server
kutt_environment_variables_smtp_host: ""

# Set the port number of the SMTP server
kutt_environment_variables_smtp_port: 587

# Set the username for the SMTP server
kutt_environment_variables_smtp_user: ""

# Set the password for the SMTP server
kutt_environment_variables_smtp_password: ""

# Set the email address that emails will be sent from
kutt_environment_variables_smtp_from: ""

# Set to `true` if SSL is used for communication with the SMTP server
kutt_environment_variables_smtp_secure: false
```

⚠️ **Note**: without setting an authentication method such as DKIM, SPF, and DMARC for your hostname, emails are most likely to be quarantined as spam at recipient's mail servers. If you have set up a mail server with the [MASH project's exim-relay Ansible role](https://github.com/mother-of-all-self-hosting/ansible-role-exim-relay), you can enable DKIM signing with it. Refer [its documentation](https://github.com/mother-of-all-self-hosting/ansible-role-exim-relay/blob/main/docs/configuring-exim-relay.md#enable-dkim-support-optional) for details.

### Configuring rate limit

By default the role enables the API rate limit. To disable it, add the following configuration to your `vars.yml` file:

```yaml
kutt_environment_variables_enable_rate_limit: false
```

### Extending the configuration

There are some additional things you may wish to configure about the component.

Take a look at:

- [`defaults/main.yml`](../defaults/main.yml) for some variables that you can customize via your `vars.yml` file. You can override settings (even those that don't have dedicated playbook variables) using the `kutt_environment_variables_additional_variables` variable

See [the official documentation](https://github.com/thedevs-network/kutt/blob/main/.example.env) for a complete list of Kutt's config options that you could put in `kutt_environment_variables_additional_variables`.

## Installing

After configuring the playbook, run the installation command of your playbook as below:

```sh
ansible-playbook -i inventory/hosts setup.yml --tags=setup-all,start
```

If you use the MASH playbook, the shortcut commands with the [`just` program](https://github.com/mother-of-all-self-hosting/mash-playbook/blob/main/docs/just.md) are also available: `just install-all` or `just setup-all`

## Usage

After running the command for installation, Kutt becomes available at the specified hostname like `https://example.com`.

To get started, open the URL with a web browser, and register the administrator account. You can create additional users (admin-privileged or not) after that.

## Troubleshooting

### Check the service's logs

You can find the logs in [systemd-journald](https://www.freedesktop.org/software/systemd/man/systemd-journald.service.html) by logging in to the server with SSH and running `journalctl -fu kutt` (or how you/your playbook named the service, e.g. `mash-kutt`).
