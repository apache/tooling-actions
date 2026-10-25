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
# dependencies = ["swh.model>=8.4.1"]
# ///

"""Compute the SWHID of the source tree contained in a release archive.

The entries of the tar stream are hashed as they are read, without extracting them,
and the directory SWHID (https://swhid.org/) of its single top-level directory
is computed with swh.model (https://gitlab.softwareheritage.org/swh/devel/swh-model).
For an archive created by git archive, it is swh:1:dir:<tree id> of the archived tree,
unless git attributes altered the archive content:
export-ignore and export-subst,
but also line ending conversion (text, eol, core.autocrlf) and clean/smudge filters,
since git archive applies the same conversions as a checkout.

The results are printed as key=value lines, which can be appended to GITHUB_OUTPUT:
swhid and swh-model-version.
"""

import argparse
import importlib.metadata
import os
import sys
import tarfile
from pathlib import Path
from typing import IO

from swh.model.hashutil import MultiHash
from swh.model.model import Directory, DirectoryEntry

DIRECTORY = 0o040000
FILE = 0o100644
EXECUTABLE = 0o100755
SYMLINK = 0o120000

# A directory maps entry names to subdirectories or to (permissions, sha1_git) pairs of files.
Tree = dict[bytes, "Tree | tuple[int, bytes]"]


class Error(Exception):
    pass


def blob_id(data: IO[bytes], length: int) -> bytes:
    return MultiHash.from_file(data, hash_names=["sha1_git"], length=length).digest()["sha1_git"]


def directory_id(tree: Tree) -> bytes:
    entries = []
    for name, node in tree.items():
        if isinstance(node, dict):
            entries.append(DirectoryEntry(name=name, type="dir", perms=DIRECTORY, target=directory_id(node)))
        else:
            perms, target = node
            entries.append(DirectoryEntry(name=name, type="file", perms=perms, target=target))
    return Directory(entries=tuple(entries)).id


def tar_swhid(fileobj: IO[bytes], archive_directory: str = "") -> str:
    """Return the directory SWHID of the single top-level directory of a tar stream, compressed or not."""
    root: Tree = {}
    with tarfile.open(fileobj=fileobj, mode="r|*") as tar:
        for member in tar:
            parts = [os.fsencode(part) for part in member.name.split("/")]
            if member.name.startswith("/") or any(part in (b"", b".", b"..") for part in parts):
                raise Error(f"Unsupported path in the archive: {member.name}")
            parent = root
            for part in parts[:-1]:
                parent = parent.setdefault(part, {})
                if not isinstance(parent, dict):
                    raise Error(f"Unsupported path in the archive: {member.name}")
            name = parts[-1]
            if member.isdir():
                if not isinstance(parent.setdefault(name, {}), dict):
                    raise Error(f"Unsupported path in the archive: {member.name}")
            elif member.isreg():
                perms = EXECUTABLE if member.mode & 0o111 else FILE
                parent[name] = (perms, blob_id(tar.extractfile(member), member.size))
            elif member.issym():
                target = os.fsencode(member.linkname)
                parent[name] = (SYMLINK, MultiHash.from_data(target, hash_names=["sha1_git"]).digest()["sha1_git"])
            else:
                raise Error(f"Unsupported entry type in the archive: {member.name}")

    entries = sorted(os.fsdecode(name) for name in root)
    if len(entries) != 1 or (archive_directory and entries != [archive_directory]):
        expected = f"the single directory {archive_directory}/" if archive_directory else "a single directory"
        raise Error(f"Expected the archive to contain {expected}, found: {entries}")
    top = root[os.fsencode(entries[0])]
    if not isinstance(top, dict):
        raise Error(f"Expected the archive to contain a single directory, found the file {entries[0]}")
    return f"swh:1:dir:{directory_id(top).hex()}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archive", type=Path, help="source archive (.tar, .tar.gz, .tar.bz2 or .tar.xz)")
    parser.add_argument("--archive-directory", default="", help="expected name of the single top-level directory inside the archive")
    args = parser.parse_args(argv)

    try:
        with args.archive.open("rb") as archive:
            swhid = tar_swhid(archive, args.archive_directory)
    except (Error, tarfile.TarError) as e:
        sys.exit(f"error: {e}")

    print(f"swhid={swhid}")
    print(f"swh-model-version={importlib.metadata.version('swh.model')}")


if __name__ == "__main__":
    main()
