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

"""Compute the SWHID of the source tree contained in the release archive.

The archive is extracted into a temporary directory,
and the directory SWHID (https://swhid.org/) of its single top-level directory
is computed with asfswhid (https://github.com/apache/tooling-asfswhid).
The result is compared with the SWHID of the archived git tree.
They are identical unless git attributes altered the archive content:
export-ignore and export-subst,
but also line ending conversion (text, eol, core.autocrlf) and clean/smudge filters,
since git archive applies the same conversions as a checkout.

Inputs (environment): DIRECTORY, ARCHIVE, ARCHIVE_DIRECTORY, TREE
Outputs (GITHUB_OUTPUT): swhid
"""

import os
import sys
import tarfile
import tempfile
from pathlib import Path

from asfswhid import directory_id


def error(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    directory = Path(os.environ["DIRECTORY"])
    archive = os.environ["ARCHIVE"]
    archive_directory = os.environ["ARCHIVE_DIRECTORY"]
    tree = os.environ["TREE"]

    with tempfile.TemporaryDirectory(prefix="upload-source-to-atr-") as tmp:
        with tarfile.open(directory / archive, "r:gz") as tar:
            tar.extractall(tmp, filter="data")
        entries = sorted(os.listdir(tmp))
        if entries != [archive_directory]:
            error(f"Expected {archive} to contain the single directory {archive_directory}/, found: {entries}")
        swhid = str(directory_id(os.path.join(tmp, archive_directory)))

    tree_swhid = f"swh:1:dir:{tree}" if len(tree) == 40 else None
    if tree_swhid is None:
        comparison = "not compared with the git tree (repository does not use SHA-1)"
    elif swhid == tree_swhid:
        comparison = "identical to the git tree of the archived commit"
    else:
        comparison = f"differs from the git tree `{tree_swhid}`, git attributes such as export-ignore, export-subst or eol altered the content"

    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"swhid={swhid}\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write(f"- SWHID: `{swhid}` ({comparison})\n")
    print(f"{swhid} ({comparison})")


if __name__ == "__main__":
    main()
