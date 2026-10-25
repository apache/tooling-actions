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

import gzip
import hashlib
import subprocess
import tarfile
import zlib
from pathlib import Path

import pytest

import archive
from conftest import ARCHIVE_SHA512, COMMIT, COMMIT_TIME, SWHID, TREE, commit, git, parse_outputs

NAME = "apache-example-1.2.3-src"


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("example", "1.2.3"), ("apache-example-1.2.3-src.tar.gz", "apache-example-1.2.3-src")),
        (("example", "1.2.3", "example-1.2.3"), ("example-1.2.3.tar.gz", "example-1.2.3")),
        (("example", "1.2.3", "", "example"), ("apache-example-1.2.3-src.tar.gz", "example")),
        (("example", "1.2.3", "example-1.2.3", "example"), ("example-1.2.3.tar.gz", "example")),
    ],
)
def test_archive_names(arguments: tuple[str, ...], expected: tuple[str, str]) -> None:
    assert archive.archive_names(*arguments) == expected


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("", "1.2.3"), "project"),
        (("example", "1.2.3/../.."), "version"),
        (("example", "-1.2.3"), "version"),
        (("example", "1.2.3", "example 1.2.3"), "archive-prefix"),
        (("example", "1.2.3", "", "../example"), "archive-directory"),
        (("example", "1.2.3", "example-1.2.3.tar.gz"), "suffix"),
        (("example", "1.2.3", "example-1.2.3.tgz"), "suffix"),
    ],
)
def test_archive_names_invalid(arguments: tuple[str, ...], message: str) -> None:
    with pytest.raises(archive.Error, match=message):
        archive.archive_names(*arguments)


def test_archive(repository: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    directory = tmp_path / "dist"

    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(directory)])

    name = "apache-example-1.2.3-src.tar.gz"
    assert [path.name for path in directory.iterdir()] == [name]
    sha512 = hashlib.sha512((directory / name).read_bytes()).hexdigest()

    with tarfile.open(directory / name) as tar:
        members = {member.name: member for member in tar.getmembers()}
    prefix = "apache-example-1.2.3-src"
    assert sorted(members) == [prefix, f"{prefix}/README.md", f"{prefix}/build.sh", f"{prefix}/src", f"{prefix}/src/main.py"]
    assert members[f"{prefix}/build.sh"].mode == 0o755
    assert members[f"{prefix}/README.md"].mode == 0o644
    assert all(member.uname == "root" and member.mtime == COMMIT_TIME for member in members.values())

    outputs = parse_outputs(capsys.readouterr().out)
    assert outputs == {
        "directory": str(directory),
        "archive": name,
        "archive-directory": prefix,
        "commit": COMMIT,
        "tree": TREE,
        "sha512": sha512,
        "swhid": SWHID,
        **archive.diagnostics(),
    }


def test_archive_is_reproducible(repository: Path, tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(first)])
    # A different checkout time and umask must not change the archive.
    (repository / "README.md").touch()
    (repository / "README.md").chmod(0o666)
    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(second)])

    name = "apache-example-1.2.3-src.tar.gz"
    assert (first / name).read_bytes() == (second / name).read_bytes()


def test_archive_commit(repository: Path, tmp_path: Path) -> None:
    git(repository, "tag", "v1.2.3")
    (repository / "NEW.md").write_text("New\n", encoding="utf-8")
    git(repository, "add", "NEW.md")
    commit(repository, "Second commit")

    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--commit", "v1.2.3", "--output-directory", str(tmp_path)])

    with tarfile.open(tmp_path / "apache-example-1.2.3-src.tar.gz") as tar:
        assert "apache-example-1.2.3-src/NEW.md" not in tar.getnames()


def test_archive_default_repository(repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repository / "src")

    archive.main(["--project", "example", "--version", "1.2.3", "--output-directory", str(tmp_path)])

    # The whole repository, not only the current subdirectory
    with tarfile.open(tmp_path / "apache-example-1.2.3-src.tar.gz") as tar:
        assert "apache-example-1.2.3-src/README.md" in tar.getnames()


def test_archive_without_commit(tmp_path: Path) -> None:
    git(tmp_path, "init", "--quiet")

    with pytest.raises(SystemExit) as exit_info:
        archive.main(["--repository", str(tmp_path), "--project", "example", "--version", "1.2.3", "--output-directory", str(tmp_path / "dist")])

    assert str(exit_info.value).startswith(f"error: No git commit found for 'HEAD' in {tmp_path}")
    assert not (tmp_path / "dist").exists()


def test_archive_not_a_repository(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="is not a git repository"):
        archive.main(["--repository", str(tmp_path / "missing"), "--project", "example", "--version", "1.2.3", "--output-directory", str(tmp_path)])


def test_archive_compression(repository: Path, tmp_path: Path) -> None:
    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(tmp_path)])
    path = tmp_path / f"{NAME}.tar.gz"
    tar = subprocess.run(
        ["git", "-C", repository, "-c", "tar.umask=0022", "archive", "--format=tar", f"--prefix={NAME}/", "HEAD"],
        check=True,
        capture_output=True,
    ).stdout

    # Same output as the gzip module, with the commit time as timestamp
    assert path.read_bytes() == gzip.compress(tar, compresslevel=9, mtime=COMMIT_TIME)
    with gzip.open(path) as compressed:
        compressed.read()
        assert compressed.mtime == COMMIT_TIME
    # Readable by gzip itself
    assert subprocess.run(["gzip", "-d", "-c", path], check=True, capture_output=True).stdout == tar


@pytest.mark.skipif(archive.uses_zlib_ng(), reason="zlib-ng compresses differently from zlib")
def test_archive_checksum(repository: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(tmp_path)])

    assert hashlib.sha512((tmp_path / f"{NAME}.tar.gz").read_bytes()).hexdigest() == ARCHIVE_SHA512
    assert parse_outputs(capsys.readouterr().out)["sha512"] == ARCHIVE_SHA512


def test_diagnostics() -> None:
    values = archive.diagnostics()

    assert list(values) == [
        "python-version",
        "platform",
        "zlib-version",
        "zlib-runtime-version",
        *(["zlib-ng-version"] if hasattr(zlib, "ZLIBNG_VERSION") else []),
        "git-version",
        "swh-model-version",
    ]
    assert values["git-version"][0].isdigit()
    assert all(value and "\n" not in value for value in values.values())
