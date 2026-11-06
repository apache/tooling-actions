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

"""Create a reproducible source archive of a git commit, with its SHA-512 checksum and SWHID.

See https://reproducible-builds.org/docs/archives/

git archive uses the commit time as mtime and root as owner,
and tar.umask normalizes permissions.
The tar stream is compressed with the gzip module at level 9,
without file name and with the commit time as timestamp in the gzip header.
Anyone who archives the same commit with Python and zlib (but not zlib-ng)
obtains a byte-for-byte identical file.

The tar stream is read once: while it is compressed,
its entries are hashed to compute the SWHID (see swhid.py),
and the compressed output is hashed to compute the SHA-512 checksum.

The results are printed as key=value lines, which can be appended to GITHUB_OUTPUT:
directory, archive, archive-directory, commit, tree, sha512 and swhid,
followed by the versions of the tools that can affect the result:
python-version, platform, zlib-version, zlib-runtime-version, zlib-ng-version (if any), git-version and swh-model-version.
"""

import argparse
import gzip
import hashlib
import importlib.metadata
import platform
import re
import subprocess
import sys
import tarfile
import zlib
from pathlib import Path
from typing import IO

from swhid import Error as SwhidError
from swhid import tar_swhid

NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


class Error(Exception):
    pass


def check_name(value: str, description: str) -> str:
    if not NAME_PATTERN.fullmatch(value):
        raise Error(f"{description} must only contain letters, digits, '.', '_', '+' or '-'")
    return value


def archive_names(project: str, version: str, archive_prefix: str = "", archive_directory: str = "") -> tuple[str, str]:
    """Return the archive file name and the name of its top-level directory."""
    check_name(project, "project")
    check_name(version, "version")
    archive_prefix = archive_prefix or f"apache-{project}-{version}-src"
    archive_directory = archive_directory or archive_prefix
    check_name(archive_prefix, "archive-prefix")
    check_name(archive_directory, "archive-directory")
    if archive_prefix.endswith((".tar.gz", ".tgz", ".tar")):
        raise Error("archive-prefix must not include the .tar.gz suffix; it is appended automatically")
    return f"{archive_prefix}.tar.gz", archive_directory


def top_level(repository: Path) -> Path:
    """Return the top-level directory of the repository, since git archive only archives the current subdirectory."""
    result = subprocess.run(["git", "-C", repository, "rev-parse", "--show-cdup"], capture_output=True, text=True)
    if result.returncode != 0:
        raise Error(f"{repository} is not a git repository; check out the repository first (actions/checkout)")
    return repository / result.stdout.strip()


def resolve(repository: Path, revision: str, kind: str) -> str:
    result = subprocess.run(
        ["git", "-C", repository, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{revision}^{{{kind}}}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise Error(f"No git {kind} found for {revision!r} in {repository}; check out the repository first (actions/checkout)")
    return result.stdout.strip()


def commit_time(repository: Path, commit: str) -> int:
    """Return the committer time of the commit, which git archive uses as mtime of the entries."""
    result = subprocess.run(["git", "-C", repository, "log", "-1", "--format=%ct", commit], check=True, capture_output=True, text=True)
    return int(result.stdout)


def uses_zlib_ng() -> bool:
    """zlib-ng compresses differently from zlib, so the archive would not be reproducible elsewhere."""
    return hasattr(zlib, "ZLIBNG_VERSION") or "zlib-ng" in zlib.ZLIB_RUNTIME_VERSION


class Tee:
    """Copy everything read from a stream to a sink."""

    def __init__(self, source: IO[bytes], sink: IO[bytes]) -> None:
        self.source = source
        self.sink = sink

    def read(self, size: int = -1) -> bytes:
        data = self.source.read(size)
        self.sink.write(data)
        return data


class Checksum:
    """Compute the SHA-512 checksum of everything written to a file."""

    def __init__(self, output: IO[bytes]) -> None:
        self.output = output
        self.sha512 = hashlib.sha512()

    def write(self, data: bytes) -> int:
        self.sha512.update(data)
        return self.output.write(data)

    def flush(self) -> None:
        self.output.flush()


def create_archive(repository: Path, commit: str, archive_directory: str, path: Path) -> tuple[str, str]:
    """Create the archive and return its SHA-512 checksum and its SWHID."""
    mtime = commit_time(repository, commit)
    with (
        subprocess.Popen(
            ["git", "-C", repository, "-c", "tar.umask=0022", "archive", "--format=tar", f"--prefix={archive_directory}/", commit],
            stdout=subprocess.PIPE,
        ) as git,
        path.open("wb") as output,
    ):
        checksum = Checksum(output)
        # GzipFile always writes 255 (unknown) as operating system in the header.
        with gzip.GzipFile(filename="", mode="wb", fileobj=checksum, compresslevel=9, mtime=mtime) as compressed:
            stream = Tee(git.stdout, compressed)
            swhid = tar_swhid(stream, archive_directory)
            # Copy the rest of the stream, such as the padding after the last tar entry.
            while stream.read(1 << 20):
                pass
    if git.returncode != 0:
        raise Error(f"Failed to create {path.name}")
    return checksum.sha512.hexdigest(), swhid


def diagnostics() -> dict[str, str]:
    """Return the versions of the tools that can affect the archive or its SWHID."""
    git = subprocess.run(["git", "--version"], check=True, capture_output=True, text=True).stdout.strip()
    values = {
        "python-version": platform.python_version(),
        "platform": platform.platform(),
        "zlib-version": zlib.ZLIB_VERSION,
        "zlib-runtime-version": zlib.ZLIB_RUNTIME_VERSION,
    }
    if hasattr(zlib, "ZLIBNG_VERSION"):
        values["zlib-ng-version"] = zlib.ZLIBNG_VERSION
    values["git-version"] = git.removeprefix("git version ")
    values["swh-model-version"] = importlib.metadata.version("swh.model")
    return values


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", required=True, help="ATR project")
    parser.add_argument("--version", required=True, help="ATR release version")
    parser.add_argument("--archive-prefix", default="", help="archive file name without the .tar.gz suffix (default: apache-<project>-<version>-src)")
    parser.add_argument("--archive-directory", default="", help="name of the single top-level directory inside the archive (default: same as --archive-prefix)")
    parser.add_argument("--repository", type=Path, default=Path(), help="git repository to archive (default: current directory)")
    parser.add_argument("--commit", default="HEAD", help="commit to archive (default: HEAD)")
    parser.add_argument("--output-directory", type=Path, default=Path(), help="directory to write the archive to (default: current directory)")
    args = parser.parse_args(argv)

    if uses_zlib_ng():
        print("warning: Python uses zlib-ng, which compresses differently from zlib: the archive is not reproducible with zlib", file=sys.stderr)

    try:
        archive, archive_directory = archive_names(args.project, args.version, args.archive_prefix, args.archive_directory)
        repository = top_level(args.repository)
        commit = resolve(repository, args.commit, "commit")
        tree = resolve(repository, commit, "tree")
        directory = args.output_directory.resolve()
        directory.mkdir(parents=True, exist_ok=True)
        sha512, swhid = create_archive(repository, commit, archive_directory, directory / archive)
    except (Error, SwhidError, tarfile.TarError) as e:
        sys.exit(f"error: {e}")

    results = {
        "directory": str(directory),
        "archive": archive,
        "archive-directory": archive_directory,
        "commit": commit,
        "tree": tree,
        "sha512": sha512,
        "swhid": swhid,
    }
    for key, value in (results | diagnostics()).items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
