# ASF Tooling Actions

This repository contains GitHub Actions written and maintained by the **Apache Software Foundation (ASF) Tooling team**.

**Note:** ASF Tooling is an operational team. Unlike Project Management Committees (PMCs), we do not make Board-approved releases.

If you are looking for infrastructure-related actions, please visit [ASF Infrastructure Actions](https://github.com/apache/infrastructure-actions) instead.

## Versioning Policy

**We do not tag versions.** For security and stability, you must refer to every action by its **pinned commit hash** (SHA). Do not use `@main` or `@v1`.

## Available Actions

### `apache/tooling-actions/upload-to-atr`

![Status: Production](https://img.shields.io/badge/Status-PRODUCTION-blue)

Upload your artifacts to the Apache Trusted Release (ATR) system using OIDC and an ephemeral SSH key, as part of the [ATR Trusted Publishing](https://releases.apache.org/docs/trusted-publishing) workflow.

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
```

### `apache/tooling-actions/release-on-atr`

![Status: Production](https://img.shields.io/badge/Status-PRODUCTION-blue)

Resolve the vote on a release candidate, announce a release, or both, on the Apache Trusted Release (ATR) system using OIDC, as part of the [ATR Trusted Publishing](https://releases.apache.org/docs/trusted-publishing) workflow. See the [README](release-on-atr/README.md) for the inputs and the release policy that ATR needs.

#### Usage Example

```yaml
jobs:
  announce:
    runs-on: ubuntu-latest
    permissions:
      id-token: write # Required for OIDC
      contents: read
    steps:
      - name: Announce on ATR
        uses: apache/tooling-actions/release-on-atr@<COMMIT_HASH>
        with:
          version: 1.2.3
          announce: "true"
          announce-email-to: announce@apache.org
          announce-body: |
            The Apache Example team is pleased to announce...
```
