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
import shutil
import subprocess
from pathlib import Path

import pytest

import archive
import sign

FINGERPRINT = "0123456789ABCDEF0123456789ABCDEF01234567"


@pytest.mark.parametrize("expected", ["", FINGERPRINT, FINGERPRINT.lower()])
def test_check_fingerprint(expected: str) -> None:
    sign.check_fingerprint(FINGERPRINT, expected)


@pytest.mark.parametrize(
    ("expected", "message"),
    [
        ("89ABCDEF01234567", "full fingerprint"),
        (f"0x{FINGERPRINT}", "full fingerprint"),
        ("F" * 40, "does not match"),
    ],
)
def test_check_fingerprint_invalid(expected: str, message: str) -> None:
    with pytest.raises(sign.Error, match=message):
        sign.check_fingerprint(FINGERPRINT, expected)


SUBKEY = "FEDCBA9876543210FEDCBA9876543210FEDCBA98"


@pytest.mark.parametrize(
    ("status", "fingerprint", "valid"),
    [
        (f"[GNUPG:] VALIDSIG {FINGERPRINT} 2026-01-01 1767225600 0 4 0 1 10 00 {FINGERPRINT}", FINGERPRINT, True),
        (f"[GNUPG:] VALIDSIG {SUBKEY} 2026-01-01 1767225600 0 4 0 1 10 00 {FINGERPRINT}", FINGERPRINT, True),
        (f"[GNUPG:] VALIDSIG {SUBKEY} 2026-01-01 1767225600 0 4 0 1 10 00 {FINGERPRINT}", SUBKEY, True),
        (f"[GNUPG:] VALIDSIG {FINGERPRINT} 2026-01-01 1767225600 0 4 0 1 10 00 {FINGERPRINT}", FINGERPRINT.lower(), True),
        (f"[GNUPG:] GOODSIG {FINGERPRINT[-16:]} Test", FINGERPRINT, False),
        (f"[GNUPG:] VALIDSIG {SUBKEY} 2026-01-01 1767225600 0 4 0 1 10 00 {SUBKEY}", FINGERPRINT, False),
        ("[GNUPG:] VALIDSIG", FINGERPRINT, False),
        ("", FINGERPRINT, False),
    ],
)
def test_has_valid_signature(status: str, fingerprint: str, valid: bool) -> None:
    assert sign.has_valid_signature(f"[GNUPG:] NEWSIG\n{status}\n", fingerprint) is valid


@pytest.fixture
def gpg_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Generate a throw-away signing key in a temporary GnuPG home and return its fingerprint."""
    if shutil.which("gpg") is None:
        pytest.skip("gpg is not installed")
    home = tmp_path / "gnupg"
    home.mkdir(mode=0o700)
    monkeypatch.setenv("GNUPGHOME", str(home))
    subprocess.run(
        ["gpg", "--batch", "--quiet", "--passphrase", "", "--quick-generate-key", "Test <test@example.org>", "ed25519", "sign", "never"],
        check=True,
    )
    yield next(
        line.split(":")[9]
        for line in subprocess.run(["gpg", "--batch", "--with-colons", "--list-secret-keys"], check=True, capture_output=True, text=True).stdout.splitlines()
        if line.startswith("fpr:")
    )
    subprocess.run(["gpgconf", "--kill", "all"], check=False, env={**os.environ, "GNUPGHOME": str(home)})


def test_sign(repository: Path, tmp_path: Path, gpg_key: str) -> None:
    directory = tmp_path / "dist"
    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(directory)])
    path = directory / "apache-example-1.2.3-src.tar.gz"

    sign.main([str(path), "--fingerprint", gpg_key, "--expected-fingerprint", gpg_key.lower()])

    subprocess.run(["gpg", "--batch", "--verify", f"{path}.asc", path], check=True)


def test_sign_wrong_key(repository: Path, tmp_path: Path, gpg_key: str) -> None:
    archive.main(["--repository", str(repository), "--project", "example", "--version", "1.2.3", "--output-directory", str(tmp_path)])
    path = tmp_path / "apache-example-1.2.3-src.tar.gz"

    with pytest.raises(SystemExit, match="does not match"):
        sign.main([str(path), "--fingerprint", gpg_key, "--expected-fingerprint", FINGERPRINT])
    assert not path.with_name(f"{path.name}.asc").exists()
