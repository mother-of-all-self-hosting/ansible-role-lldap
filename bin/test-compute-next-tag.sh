#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Slavi Pantaleev
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# Exercises bin/compute-next-tag.sh against throwaway git repositories.
#
# Usage: bin/test-compute-next-tag.sh
#
# Every scenario creates a repository in a temporary directory, gives it role
# files and a release history, and then replays a series of merges through the
# real script, tagging as it goes just like the autotag workflow does. This
# repository is never touched and no network access is needed.

set -euo pipefail

script_under_test="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/compute-next-tag.sh"

failures=0
workdir=''

cleanup() {
	cd /
	if [ -n "$workdir" ]; then
		rm -rf "$workdir"
		workdir=''
	fi
}

trap cleanup EXIT

# Starts a scenario with a repository at LLDAP v0.6.3 which has already seen
# three releases of it - the tag names this repository really carries
# (v0.6.3-0, v0.6.3-1, v0.6.3-2), so that the numbering the script computes is
# the numbering the repository already uses.
#
# The defaults file deliberately carries the traps this role's real one has:
# a longer variable name that starts with `lldap_version`'s text, a variable
# whose value is derived from `lldap_version`, and a commented-out
# `lldap_version` line. None of them may be picked up as the version.
scenario() {
	echo "$1"

	cleanup
	workdir="$(mktemp -d)"

	mkdir -p "$workdir/bin" "$workdir/defaults" "$workdir/meta" "$workdir/tasks" "$workdir/templates"
	cp "$script_under_test" "$workdir/bin/"
	cd "$workdir"

	git init -q -b main .
	git config user.email 'test@example.com'
	git config user.name 'Test'
	git config commit.gpgsign false

	cat > defaults/main.yml <<-'YAML'
		# lldap_version: v9.9.9
		lldap_version: v0.6.3
		lldap_version_note: irrelevant
		lldap_container_image_tag: "{{ lldap_version }}-alpine-rootless"
		lldap_container_image_self_build_repo_version: "{{ lldap_version if lldap_version != 'latest' else 'main' }}"
	YAML
	printf 'placeholder\n' > meta/main.yml
	printf 'placeholder\n' > tasks/main.yml
	printf 'placeholder\n' > templates/env.j2
	printf 'placeholder\n' > README.md

	git add -A
	git commit -qm 'Initial commit'

	local release_number
	for release_number in 0 1 2; do
		git tag "v0.6.3-$release_number"
	done
}

# Applies a change, commits it, and tags whatever the script says it should be.
# Prints the tag, or nothing when the script decided against a release.
merge() {
	local change="$1" tag

	eval "$change"
	git add -A
	git commit -qm 'Merge'

	tag="$(bin/compute-next-tag.sh 2>/dev/null)"

	if [ -n "$tag" ]; then
		git tag "$tag"
	fi

	printf '%s' "$tag"
}

expect() {
	local description="$1" expected="$2" actual="$3"

	if [ "$actual" = "$expected" ]; then
		printf '  ok   | %s -> %s\n' "$description" "${actual:-no release}"
	else
		printf '  FAIL | %s -> expected %s, got %s\n' "$description" "${expected:-no release}" "${actual:-no release}"
		failures=$((failures + 1))
	fi
}

bump_version="sed -i 's|^lldap_version: v0.6.3|lldap_version: v0.6.4|' defaults/main.yml"
revert_version="sed -i 's|^lldap_version: v0.6.4|lldap_version: v0.6.3|' defaults/main.yml"
edit_task="printf 'a task\n' >> tasks/main.yml"
edit_template="printf 'a line\n' >> templates/env.j2"
edit_meta="printf 'metadata\n' >> meta/main.yml"
edit_readme="printf 'documentation\n' >> README.md"
edit_script="printf '# a comment\n' >> bin/compute-next-tag.sh"

# The two merge orders below apply the same updates and must each end up with
# every update released exactly once, whichever order they arrive in.

scenario 'A version bump merged before other role changes'
expect 'version bump' v0.6.4-0 "$(merge "$bump_version")"
expect 'task edit'    v0.6.4-1 "$(merge "$edit_task")"
expect 'template'     v0.6.4-2 "$(merge "$edit_template")"

scenario 'A version bump merged after other role changes'
expect 'task edit'    v0.6.3-3 "$(merge "$edit_task")"
expect 'version bump' v0.6.4-0 "$(merge "$bump_version")"

scenario 'Changes to each of the role-defining paths'
expect 'meta'     v0.6.3-3 "$(merge "$edit_meta")"
expect 'template' v0.6.3-4 "$(merge "$edit_template")"

scenario 'Commits that do not affect the role'
expect 'README'   ''         "$(merge "$edit_readme")"
expect 'a script' ''         "$(merge "$edit_script")"
expect 'a task'   v0.6.3-3   "$(merge "$edit_task")"

# The version is read from a single anchored line. Neither the commented-out
# one, nor `lldap_version_note`, nor the two variables that interpolate
# `lldap_version` may be mistaken for it - each would name a tag that upstream
# never released.
scenario 'Lines in defaults/main.yml that look like the version'
expect 'a task' v0.6.3-3 "$(merge "$edit_task")"

scenario 'Release numbers past 9'
for release_number in 3 4 5 6 7 8 9 10; do
	git tag "v0.6.3-$release_number"
done
expect 'a task' v0.6.3-11 "$(merge "$edit_task")"

scenario 'Reverting to an already released version'
merge "$bump_version" > /dev/null
# The role is now identical to what v0.6.3-2 already published, so there is
# nothing new to release.
expect 'a revert' ''       "$(merge "$revert_version")"

scenario 'Reverting to an already released version, with a change'
merge "$bump_version" > /dev/null
expect 'a revert' v0.6.3-3 "$(merge "$revert_version && $edit_task")"

if [ "$failures" -gt 0 ]; then
	echo >&2 "$failures scenario(s) behaved unexpectedly"
	exit 1
fi

echo 'All scenarios behaved as expected'
