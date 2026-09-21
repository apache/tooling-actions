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

# Sign the source archive with the imported GPG key and verify the signature and checksum.
#
# Inputs (environment): DIRECTORY, ARCHIVE, IMPORTED_FINGERPRINT, EXPECTED_FINGERPRINT

set -euo pipefail

if [[ -n "$EXPECTED_FINGERPRINT" ]]; then
  if ! [[ "$EXPECTED_FINGERPRINT" =~ ^([0-9A-Fa-f]{40}|[0-9A-Fa-f]{64})$ ]]; then
    echo "::error::gpg-fingerprint must be the full fingerprint of the primary key (40 or 64 hex digits)"
    exit 1
  fi
  if [[ "${IMPORTED_FINGERPRINT^^}" != "${EXPECTED_FINGERPRINT^^}" ]]; then
    echo "::error::The imported GPG key (${IMPORTED_FINGERPRINT}) does not match gpg-fingerprint"
    exit 1
  fi
fi

cd "$DIRECTORY"
gpg --batch --yes --armor --detach-sign --local-user "$IMPORTED_FINGERPRINT" --output "${ARCHIVE}.asc" "$ARCHIVE"
gpg --batch --status-fd 1 --verify "${ARCHIVE}.asc" "$ARCHIVE" |
  awk -v fingerprint="$IMPORTED_FINGERPRINT" \
    '$1 == "[GNUPG:]" && $2 == "VALIDSIG" && ($3 == fingerprint || $NF == fingerprint) { valid = 1 } END { exit !valid }'
sha512sum --check "${ARCHIVE}.sha512"

echo "- Signed with: \`${IMPORTED_FINGERPRINT}\`" >> "$GITHUB_STEP_SUMMARY"
