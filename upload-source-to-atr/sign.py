#!/usr/bin/env -S uv run --script
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

# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Sign a source archive with GPG and verify the signature.

The detached ASCII-armored signature is written next to the archive as <archive>.asc.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

FINGERPRINT_PATTERN = re.compile(r"[0-9A-Fa-f]{40}|[0-9A-Fa-f]{64}")


class Error(Exception):
    pass


def check_fingerprint(imported: str, expected: str) -> None:
    """Fail if the expected fingerprint is set and differs from the imported one."""
    if not expected:
        return
    if not FINGERPRINT_PATTERN.fullmatch(expected):
        raise Error("gpg-fingerprint must be the full fingerprint of the primary key (40 or 64 hex digits)")
    if imported.upper() != expected.upper():
        raise Error(f"The imported GPG key ({imported}) does not match gpg-fingerprint")


def has_valid_signature(status: str, fingerprint: str) -> bool:
    """Check the gpg --status-fd output for a valid signature by the key or its primary key.

    See https://github.com/gpg/gnupg/blob/master/doc/DETAILS (VALIDSIG)
    """
    fingerprint = fingerprint.upper()
    for line in status.splitlines():
        fields = line.split()
        if len(fields) > 2 and fields[:2] == ["[GNUPG:]", "VALIDSIG"] and fingerprint in (fields[2].upper(), fields[-1].upper()):
            return True
    return False


def sign(archive: Path, fingerprint: str) -> Path:
    signature = archive.with_name(f"{archive.name}.asc")
    subprocess.run(
        ["gpg", "--batch", "--yes", "--armor", "--detach-sign", "--local-user", fingerprint, "--output", signature, archive],
        check=True,
    )
    result = subprocess.run(
        ["gpg", "--batch", "--status-fd", "1", "--verify", signature, archive],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not has_valid_signature(result.stdout, fingerprint):
        sys.stderr.write(result.stderr)
        raise Error(f"The signature of {archive.name} is not a valid signature by {fingerprint}")
    return signature


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archive", type=Path, help="archive to sign")
    parser.add_argument("--fingerprint", required=True, help="fingerprint of the GPG key to sign with")
    parser.add_argument("--expected-fingerprint", default="", help="fail unless --fingerprint matches this fingerprint")
    args = parser.parse_args(argv)

    try:
        check_fingerprint(args.fingerprint, args.expected_fingerprint)
        sign(args.archive, args.fingerprint)
    except Error as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
