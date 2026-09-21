#!/usr/bin/env bash
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Create a reproducible source archive of HEAD and its SHA-512 checksum.
# See https://reproducible-builds.org/docs/archives/
#
# Inputs (environment): INPUTS_PROJECT, INPUTS_VERSION, INPUTS_ARCHIVE_PREFIX, INPUTS_ARCHIVE_DIRECTORY
# Outputs (GITHUB_OUTPUT): directory, archive, archive-directory, commit, tree, sha512

set -euo pipefail

: "${INPUTS_PROJECT:?project is required}"
: "${INPUTS_VERSION:?version is required}"
name_pattern='^[A-Za-z0-9][A-Za-z0-9._+-]*$'
for name in "$INPUTS_PROJECT" "$INPUTS_VERSION"; do
  if ! [[ "$name" =~ $name_pattern ]]; then
    echo "::error::project and version must only contain letters, digits, '.', '_', '+' or '-'"
    exit 1
  fi
done
archive_prefix="${INPUTS_ARCHIVE_PREFIX:-apache-${INPUTS_PROJECT}-${INPUTS_VERSION}-src}"
archive_directory="${INPUTS_ARCHIVE_DIRECTORY:-${archive_prefix}}"
for name in "$archive_prefix" "$archive_directory"; do
  if ! [[ "$name" =~ $name_pattern ]]; then
    echo "::error::archive-prefix and archive-directory must only contain letters, digits, '.', '_', '+' or '-'"
    exit 1
  fi
done
case "$archive_prefix" in
  *.tar.gz|*.tgz|*.tar)
    echo "::error::archive-prefix must not include the .tar.gz suffix; it is appended automatically"
    exit 1;;
esac
if ! commit="$(git rev-parse --verify --quiet 'HEAD^{commit}')"; then
  echo "::error::No git commit found in the working directory; check out the repository first (actions/checkout)"
  exit 1
fi
tree="$(git rev-parse "${commit}^{tree}")"

archive="${archive_prefix}.tar.gz"
directory="${RUNNER_TEMP}/upload-source-to-atr"
rm -rf "$directory"
mkdir "$directory"

# git archive uses the commit time as mtime and root as owner,
# tar.umask normalizes permissions,
# and gzip -n omits the file name and timestamp from the gzip header.
git -c tar.umask=0022 archive --format=tar --prefix="${archive_directory}/" "$commit" |
  gzip -n -9 > "${directory}/${archive}"

cd "$directory"
sha512sum "$archive" > "${archive}.sha512"
sha512="$(cut -d ' ' -f 1 "${archive}.sha512")"

{
  echo "directory=${directory}"
  echo "archive=${archive}"
  echo "archive-directory=${archive_directory}"
  echo "commit=${commit}"
  echo "tree=${tree}"
  echo "sha512=${sha512}"
} >> "$GITHUB_OUTPUT"
{
  echo "### Source release"
  echo
  echo "- Commit: \`${commit}\`"
  echo "- Archive: \`${archive}\` (top-level directory \`${archive_directory}/\`)"
  echo "- SHA-512: \`${sha512}\`"
} >> "$GITHUB_STEP_SUMMARY"
