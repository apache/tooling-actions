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

import os
import subprocess
from pathlib import Path

import pytest

# The repository fixture creates the same commit everywhere,
# since the contents, modes, author, committer and dates are fixed.
COMMIT = "109ec9b279c8a8ac545881da50f33a395248177d"
COMMIT_TIME = 1767225600  # 2026-01-01T00:00:00Z
TREE = "50a2a53763c562dc4e2873ade1260e6becefa7e2"
# The archive contains the tree as is, so its SWHID is the tree id.
SWHID = f"swh:1:dir:{TREE}"
# SHA-512 checksum of apache-example-1.2.3-src.tar.gz, compressed with zlib
ARCHIVE_SHA512 = "847c798df4973332f945cc6cee6882cb7ed3ce19263acf624cea099fe633afff048ccaa687aa91340a6a433c0eeda30cf9ca4df4ce293e70f0e59e168311a7d0"


def parse_outputs(stdout: str) -> dict[str, str]:
    """Parse the key=value lines printed by the scripts, in the GITHUB_OUTPUT format."""
    outputs = {}
    for line in stdout.splitlines():
        key, separator, value = line.partition("=")
        assert separator and key and key not in outputs, f"Invalid output line: {line!r}"
        outputs[key] = value
    return outputs


def git(repository: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", repository, *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the tests from the user's git configuration."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A git repository with the single commit COMMIT."""
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "--quiet", "--initial-branch=main", "--object-format=sha1")
    (repository / "README.md").write_text("Example\n", encoding="utf-8")
    (repository / "src").mkdir()
    (repository / "src" / "main.py").write_text("print('Hello')\n", encoding="utf-8")
    script = repository / "build.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    git(repository, "add", ".")
    assert commit(repository, "Initial commit") == COMMIT
    return repository


def commit(repository: Path, message: str) -> str:
    date = f"@{COMMIT_TIME} +0000"
    subprocess.run(
        ["git", "-C", repository, "-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "--quiet", "-m", message],
        check=True,
        env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
    )
    return git(repository, "rev-parse", "HEAD")
