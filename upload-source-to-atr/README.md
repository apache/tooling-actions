# Compose, sign, and upload a source release to ATR

```
apache/tooling-actions/upload-source-to-atr
```

This composite GitHub Action creates a reproducible source archive of the checked-out commit with `git archive`,
computes its SHA-512 checksum and the [SWHID](https://swhid.org/) of its content,
signs it with a GPG key,
and uploads the three files to ATR at `/<project>/<version>/` using the [`upload-to-atr`](../upload-to-atr/README.md) action.
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
- **swhid**: If `"true"`, compute the directory SWHID of the expanded archive.
  Default: `"true"`.
- **atr-host**: ATR host to upload to.
  Default: `releases.apache.org`.
  Must match `*.apache.org`.
- **ssh-port**: SSH port on ATR.
  Default: `2222`.

## Outputs

- **directory**: Directory containing `<archive-prefix>.tar.gz`, `<archive-prefix>.tar.gz.sha512` and `<archive-prefix>.tar.gz.asc`.
- **archive**: File name of the archive.
- **commit**: Commit that was archived.
- **sha512**: SHA-512 checksum of the archive.
- **swhid**: Directory SWHID (`swh:1:dir:...`) of the expanded archive.
  Empty when `swhid` is `"false"`.

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

Anyone who archives the same commit with the same version of `gzip` obtains a byte-for-byte identical file.
The action follows the [reproducible archives](https://reproducible-builds.org/docs/archives/) guidance:

- `git archive` sets the modification time of every entry to the commit time and the owner to `root`,
- `tar.umask=0022` gives every entry the same permissions regardless of the runner,
- `gzip -n` leaves the file name and timestamp out of the gzip header.

[Trusted Publishing](https://releases.apache.org/docs/trusted-publishing) at the ASF requires releases built on CI to be reproducible,
and the ASF Security team confirms this for each pipeline.
A release that consists of this source archive alone meets the requirement out of the box.

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

The action also computes the [Software Heritage identifier](https://swhid.org/) (SWHID, ISO/IEC 18670:2025) of the source tree in the archive.
A directory SWHID is derived from the names, modes, and contents of the files alone.
Timestamps, ownership, and compression play no part,
so the same sources produce the same SWHID whichever archive format carries them.

Git builds its tree ids the same way,
so the SWHID is `swh:1:dir:<tree id>` of the archived commit as long as `git archive` exported the tree as is.
The two diverge when git attributes rewrite the exported files, for example:

- `export-ignore` and `export-subst`,
- `text` and `eol` attributes or `core.autocrlf`.

To skip the SWHID computation, set `swhid` to `false`.
