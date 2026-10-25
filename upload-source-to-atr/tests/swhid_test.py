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

import io
import os
import tarfile
from pathlib import Path

import pytest
from swh.model.from_disk import Directory

import archive
import swhid
from conftest import SWHID, TREE, commit, git, parse_outputs

NAME = "apache-example-1.2.3-src"
# Tree of the commit that adds .gitattributes with "/src export-ignore"
EXPORT_IGNORE_TREE = "44c8c13623bcab53f8bc6037a468ad98890ae9dd"
# SWHID of that tree without src/, which export-ignore leaves out of the archive
EXPORT_IGNORE_SWHID = "swh:1:dir:41c879f2c7d61e0eac22c3f510404ef5daae5466"


def create_archive(repository: Path, directory: Path) -> Path:
    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(directory)])
    return directory / f"{NAME}.tar.gz"


def tar_swhid(path: Path, archive_directory: str = "") -> str:
    with path.open("rb") as file:
        return swhid.tar_swhid(file, archive_directory)


def test_swhid_matches_git_tree(repository: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = create_archive(repository, tmp_path)
    capsys.readouterr()

    swhid.main([str(path), "--archive-directory", NAME])

    outputs = parse_outputs(capsys.readouterr().out)
    assert outputs.keys() == {"swhid", "swh-model-version"}
    # The archive contains the tree as is.
    assert outputs["swhid"] == SWHID == f"swh:1:dir:{TREE}"


def test_swhid_with_export_ignore(repository: Path, tmp_path: Path) -> None:
    (repository / ".gitattributes").write_text("/src export-ignore\n", encoding="utf-8")
    git(repository, "add", ".gitattributes")
    commit(repository, "Ignore src")
    path = create_archive(repository, tmp_path)

    result = tar_swhid(path, NAME)

    assert git(repository, "rev-parse", "HEAD^{tree}") == EXPORT_IGNORE_TREE
    assert result == EXPORT_IGNORE_SWHID != f"swh:1:dir:{EXPORT_IGNORE_TREE}"


@pytest.mark.parametrize("mode", ["w", "w:gz", "w:bz2", "w:xz"])
def test_swhid_matches_from_disk(tmp_path: Path, mode: str) -> None:
    """The SWHID computed from the tar stream equals the one swh.model computes from the extracted files."""
    path = tmp_path / "test.tar"
    with tarfile.open(path, mode) as tar:
        for name, content, file_mode in [
            ("top/README.md", b"Example\n", 0o644),
            ("top/build.sh", b"#!/bin/sh\n", 0o755),
            ("top/src/main.py", b"print('Hello')\n", 0o644),
            ("top/src/\u00e9t\u00e9.txt", b"", 0o600),
            ("top/large.bin", os.urandom(3 << 20), 0o644),
        ]:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = file_mode
            tar.addfile(info, io.BytesIO(content))
        for name in ("top/empty", "top/src/empty"):
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            tar.addfile(info)
        info = tarfile.TarInfo("top/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "src/main.py"
        tar.addfile(info)
    extracted = tmp_path / "extracted"
    with tarfile.open(path) as tar:
        tar.extractall(extracted, filter="data")

    expected = str(Directory.from_disk(path=os.fsencode(extracted / "top"), max_content_length=None).swhid())

    assert tar_swhid(path, "top") == expected


def write_tar(path: Path, *names: str) -> Path:
    with tarfile.open(path, "w:gz") as tar:
        for name in names:
            info = tarfile.TarInfo(name)
            info.size = 4
            tar.addfile(info, io.BytesIO(b"test"))
    return path


def test_swhid_wrong_directory(repository: Path, tmp_path: Path) -> None:
    path = create_archive(repository, tmp_path)

    with pytest.raises(swhid.Error, match="the single directory other/"):
        tar_swhid(path, "other")


def test_swhid_multiple_directories(tmp_path: Path) -> None:
    path = write_tar(tmp_path / "test.tar.gz", "a/file", "b/file")

    with pytest.raises(swhid.Error, match="a single directory"):
        tar_swhid(path)


def test_swhid_single_file(tmp_path: Path) -> None:
    path = write_tar(tmp_path / "test.tar.gz", "file")

    with pytest.raises(swhid.Error, match="found the file file"):
        tar_swhid(path)


@pytest.mark.parametrize("name", ["a/../escape", "../escape", "/a/file", "a//file", "a/./file"])
def test_swhid_rejects_unusual_paths(tmp_path: Path, name: str) -> None:
    path = write_tar(tmp_path / "test.tar.gz", "a/file", name)

    with pytest.raises(swhid.Error, match="Unsupported path"):
        tar_swhid(path)


def test_swhid_rejects_hard_links(tmp_path: Path) -> None:
    path = tmp_path / "test.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        info = tarfile.TarInfo("a/file")
        tar.addfile(info, io.BytesIO(b""))
        info = tarfile.TarInfo("a/link")
        info.type = tarfile.LNKTYPE
        info.linkname = "a/file"
        tar.addfile(info)

    with pytest.raises(swhid.Error, match="Unsupported entry type"):
        tar_swhid(path)


def test_swhid_invalid_archive(tmp_path: Path) -> None:
    path = tmp_path / "test.tar.gz"
    path.write_bytes(b"not an archive")

    with pytest.raises(SystemExit, match="error: "):
        swhid.main([str(path)])
