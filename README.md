# ASF Tooling Actions

This repository contains GitHub Actions written and maintained by the **Apache Software Foundation (ASF) Tooling team**.

**Note:** ASF Tooling is an operational team. Unlike Project Management Committees (PMCs), we do not make Board-approved releases.

If you are looking for infrastructure-related actions, please visit [ASF Infrastructure Actions](https://github.com/apache/infrastructure-actions) instead.

## Versioning Policy

**We do not tag versions.** For security and stability, you must refer to every action by its **pinned commit hash** (SHA). Do not use `@main` or `@v1`.

## Available Actions

### `apache/tooling-actions/upload-to-atr`

![Status: Experimental](https://img.shields.io/badge/Status-EXPERIMENTAL-orange)

Upload your artifacts to the Apache Trusted Release (ATR) system using OIDC and an ephemeral SSH key.

#### Who is this for?

If you are a PMC Release Manager testing the ATR, we need your help testing this action. Please report any issues you encounter.

#### Usage Example

Add the following to your workflow `.yml` file. Ensure you replace `<COMMIT_HASH>` with the full SHA of the specific commit you wish to use.

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      id-token: write # Required for OIDC
      contents: read
    steps:
      - name: Checkout code
        uses: actions/checkout@<COMMIT_HASH>

      - name: Upload to ATR
        uses: apache/tooling-actions/upload-to-atr@<COMMIT_HASH>
        with:
          # Add specific inputs here that are required by the action
          # project: example
          # version: ${{ github.ref_name }}

### `apache/tooling-actions/upload-source-to-atr`

![Status: Experimental](https://img.shields.io/badge/Status-EXPERIMENTAL-orange)

Compose a source release candidate:
create a reproducible source archive with `git archive`,
compute its SHA-512 checksum and SWHID,
sign it with the project's GPG key
and upload the files to ATR.
See the [action README](upload-source-to-atr/README.md) for all inputs.

#### Usage Example

```yaml
jobs:
  compose:
    runs-on: ubuntu-latest
    environment: release
    permissions:
      id-token: write # Required for OIDC
      contents: read
    steps:
      - name: Checkout code
        uses: actions/checkout@<COMMIT_HASH>
        with:
          persist-credentials: false

      - name: Compose, sign and upload the source release
        uses: apache/tooling-actions/upload-source-to-atr@<COMMIT_HASH>
        with:
          project: example
          version: 1.2.3
          gpg-private-key: ${{ secrets.EXAMPLE_GPG_SECRET_KEY }}
          gpg-passphrase: ${{ secrets.EXAMPLE_GPG_PASSPHRASE }}
          gpg-fingerprint: ${{ vars.EXAMPLE_GPG_FINGERPRINT }}
```
