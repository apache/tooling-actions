# Compose, sign, and upload a source release to ATR

```
apache/tooling-actions/upload-source-to-atr
```

This composite GitHub Action creates a reproducible source archive of the checked-out commit with `git archive`,
computes its SHA-512 checksum and the [SWHID](https://swhid.org/) of its content,
signs it with a GPG key,
and uploads the archive, its signature and its checksum file to ATR at `/<project>/<version>/` using the [`upload-to-atr`](../upload-to-atr/README.md) action,
declaring the archived commit as the source commit of the upload.
Use it to compose a source release candidate from a tag or branch without long-lived ATR credentials.

Status: EXPERIMENTAL

## Inputs

- **project (required)**: ATR project name segment in the remote path.
- **version (required)**: ATR release version segment in the remote path, for example `1.2.3`.
- **archive-prefix**: Archive file name without the `.tar.gz` suffix.
  Default: `apache-<project>-<version>-src`.
- **archive-directory**: Name of the single top-level directory inside the archive.
  Default: same as `archive-prefix`.
- **gpg-private-key (required)**: ASCII-armored GPG private key used for signing.
- **gpg-passphrase**: Passphrase of the GPG private key, if it has one.
  Default: empty.
- **gpg-fingerprint**: Expected fingerprint of the primary signing key.
  When set, the action fails if the imported key has a different fingerprint.
  Default: empty (no check).
- **atr-host**: ATR host to upload to.
  Default: `releases.apache.org`.
  Must match `*.apache.org`.
- **ssh-port**: SSH port on ATR.
  Default: `2222`.

## Outputs

- **directory**: Directory containing `<archive-prefix>.tar.gz`, its signature `<archive-prefix>.tar.gz.asc`,
  and its checksum file `<archive-prefix>.tar.gz.sha512` in the format of `sha512sum`.
- **archive**: File name of the archive.
- **commit**: Commit that was archived.
- **sha512**: SHA-512 checksum of the archive.
- **swhid**: Directory SWHID (`swh:1:dir:...`) of the archived source tree.

## Example workflow

The `id-token` write permission is **required** when using this GitHub Action.
Tagged versions of this action are not available.
Replace `<COMMIT>` in this example with your chosen commit.

```yaml
name: Compose source release

on:
  push:
    tags: ["v*.*.*-rc.*"]

permissions:
  contents: read

jobs:
  compose:
    if: github.repository == 'apache/example'
    runs-on: ubuntu-latest
    # Keep the signing secrets in an environment that requires approval.
    environment:
      name: release
      url: https://releases.apache.org/projects/example
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@<COMMIT>
        with:
          persist-credentials: false

      - name: Extract version
        id: version
        run: |
          version="${GITHUB_REF_NAME#v}"
          echo "version=${version%-rc.*}" >> "$GITHUB_OUTPUT"

      - name: Compose, sign and upload the source release
        uses: apache/tooling-actions/upload-source-to-atr@<COMMIT>
        with:
          project: example
          version: ${{ steps.version.outputs.version }}
          # archive-prefix defaults to apache-example-<version>-src
          gpg-private-key: ${{ secrets.EXAMPLE_GPG_SECRET_KEY }}
          gpg-passphrase: ${{ secrets.EXAMPLE_GPG_PASSPHRASE }}
          gpg-fingerprint: ${{ vars.EXAMPLE_GPG_FINGERPRINT }}
```

## Reproducibility

Anyone who archives the same commit with `atr-archive` obtains a byte-for-byte identical file.
The action follows the [reproducible archives](https://reproducible-builds.org/docs/archives/) guidance:

- `git archive` sets the modification time of every entry to the commit time and the owner to `root`,
- `tar.umask=0022` gives every entry the same permissions regardless of the runner,
- the tar stream is compressed with Python's `gzip` module at level 9,
  without file name and with the commit time as timestamp in the gzip header.

The result does not depend on the platform's `gzip`:
it is the same as `gzip.compress(tar, compresslevel=9, mtime=<commit time>)` on any supported Python version,
but differs from the output of GNU `gzip`, which uses its own compressor.
Python builds that use [zlib-ng](https://github.com/zlib-ng/zlib-ng) instead of zlib, such as some Windows or Fedora builds,
also produce a different file, and `atr-archive` warns about it.
The Python builds that `uv` installs use zlib.

[Trusted Publishing](https://releases.apache.org/docs/trusted-publishing) at the ASF requires releases built on CI to be reproducible,
and the ASF Security team confirms this for each pipeline.
A release that consists of this source archive alone meets the requirement out of the box.

### Reproducing the archive locally

The action runs the commands of a small Python package in [`src/upload_source_to_atr`](src/upload_source_to_atr),
which requires Python 3.12 or later:

- `atr-archive` creates the source archive and computes its SHA-512 checksum and its SWHID,
- `atr-sign` signs the archive and verifies the signature,
- `atr-swhid` computes the SWHID of any existing archive.

PMC members can use them to check that a release candidate was built from the commit it claims.
Install them with [`uv`](https://docs.astral.sh/uv/) from the commit of this repository that the release workflow uses,
in place of `<ACTION_COMMIT>`:

```shell
uv tool install --managed-python \
  "git+https://github.com/apache/tooling-actions@<ACTION_COMMIT>#subdirectory=upload-source-to-atr"
```

`--managed-python` selects a Python build installed by `uv`, which uses zlib like the action.
`uv` puts the commands in `~/.local/bin`; run `uv tool update-shell` if that directory is not in your `PATH`.
`uv tool install` resolves the dependencies afresh rather than using `uv.lock`,
which does not affect the archive:
only the SWHID depends on them, and its algorithm is standardized.

With a clone of the project repository in `<REPOSITORY>`:

```shell
atr-archive --repository <REPOSITORY> --project example --version 1.2.3 --commit <COMMIT> --output-directory /tmp/check
```

The command prints its results as `key=value` lines.
The `sha512` and `swhid` values must match those of the archive on ATR.
The other lines show the versions of the tools that can affect the result,
such as `zlib-runtime-version` and `git-version`,
to compare with those in the log of the action if the checksums differ.
To compute the SWHID of the archive downloaded from ATR:

```shell
atr-swhid apache-example-1.2.3-src.tar.gz
```

Run `<command> --help` for all options.
To run the commands exactly as the action does, with the dependencies pinned by `uv.lock`,
use a clone of this repository at `<ACTION_COMMIT>` instead:

```shell
uv run --project upload-source-to-atr --frozen --no-dev --managed-python atr-archive …
```

### Signing secrets

The signing key is provisioned by ASF Infrastructure as part of [Trusted Publishing](https://releases.apache.org/docs/trusted-publishing).
Open an [INFRA ticket](https://issues.apache.org/jira/projects/INFRA/issues) and ask for a release signing key for your repository, with:

- two repository secrets holding the private key and its passphrase,
  named after the PMC, for example `EXAMPLE_GPG_SECRET_KEY` and `EXAMPLE_GPG_PASSPHRASE`,
- one organization variable holding the fingerprint of the key, for example `EXAMPLE_GPG_FINGERPRINT`,
  shared with all the repositories of the PMC.

You receive the public key, which should be added to ATR.

A composite action cannot read secrets or variables on its own,
so pass them to the `gpg-private-key`, `gpg-passphrase` and `gpg-fingerprint` inputs as in the example above.

## SWHID

The action also computes the [Software Heritage identifier](https://swhid.org/) (SWHID, ISO/IEC 18670:2025) of the source tree in the archive,
using the [`swh.model`](https://pypi.org/project/swh.model/) library maintained by Software Heritage.
The entries of the tar stream are hashed while the archive is compressed, so nothing is extracted to disk.
A directory SWHID is derived from the names, modes, and contents of the files alone.
Timestamps, ownership, and compression play no part,
so the same sources produce the same SWHID whichever archive format carries them.

Git builds its tree ids the same way,
so the SWHID is `swh:1:dir:<tree id>` of the archived commit as long as `git archive` exported the tree as is.
The two diverge when git attributes rewrite the exported files, for example:

- `export-ignore` and `export-subst`,
- `text` and `eol` attributes or `core.autocrlf`.

## Development

The commands are a small [`uv`](https://docs.astral.sh/uv/) project,
built with the `uv_build` backend.
The action pins a version of `uv` that matches the `uv_build` requirement in `pyproject.toml`,
so that `uv` builds the package itself instead of downloading `uv_build`.
`uv.lock` pins the dependencies with hashes for the action and the tests,
and Dependabot keeps it up to date.
To run the tests:

```shell
cd upload-source-to-atr
uv run pytest
```
