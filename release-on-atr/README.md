# Release on ATR using a GitHub OIDC JWT

```
apache/tooling-actions/release-on-atr
```

This composite GitHub Action exchanges a GitHub OIDC token for an ATR JWT and lets you resolve a vote or announce a release on ATR. It does not allow you to upload or modify files in the release.

Status: EXPERIMENTAL

## Inputs

- **version (required)**: Release version (e.g. `1.2.3`).
- **atr-host**: ATR host. Default: `release-test.apache.org`. Must match `*.apache.org`.
- **resolve**: If `"true"`, resolve the vote. Default: `"false"`.
- **resolve-resolution**: Resolution when resolving: `passed` or `failed`. Required when `resolve == "true"`.
- **announce**: If `"true"`, announce the release. Default: `"false"`.
- **announce-revision**: Revision number used for announcement. Required when `announce == "true"`.
- **announce-email-to**: Announcement recipient mailing list address. Required when `announce == "true"`.
- **announce-subject**: Announcement email subject. Required when `announce == "true"`.
- **announce-body**: Announcement email body. Required when `announce == "true"`.
- **announce-path-suffix**: Download path suffix. Required when `announce == "true"`.

## Example workflows

Resolve only:

```yaml
name: Resolve vote on ATR

on:
  workflow_dispatch:

jobs:
  resolve:
    permissions:
      id-token: write
      contents: read
    runs-on: ubuntu-latest
    steps:
      - name: Resolve vote
        uses: apache/tooling-actions/release-on-atr@<COMMIT>
        with:
          version: ${{ github.ref_name }}
          resolve: "true"
          resolve-resolution: passed
```

Announce only:

```yaml
name: Announce release on ATR

on:
  workflow_dispatch:

jobs:
  announce:
    permissions:
      id-token: write
      contents: read
    runs-on: ubuntu-latest
    steps:
      - name: Announce release
        uses: apache/tooling-actions/release-on-atr@<COMMIT>
        with:
          version: ${{ github.ref_name }}
          announce: "true"
          announce-revision: 00005
          announce-email-to: dev@example.apache.org
          announce-subject: "[ANNOUNCE] Apache Example ${{ github.ref_name }} released"
          announce-body: |
            The Apache Example team is pleased to announce...
          announce-path-suffix: example/${{ github.ref_name }}
```

Resolve then announce in one job:

```yaml
name: Resolve and announce on ATR

on:
  workflow_dispatch:

jobs:
  release:
    permissions:
      id-token: write
      contents: read
    runs-on: ubuntu-latest
    steps:
      - name: Resolve and announce
        uses: apache/tooling-actions/release-on-atr@<COMMIT>
        with:
          version: ${{ github.ref_name }}
          resolve: "true"
          resolve-resolution: passed
          announce: "true"
          announce-revision: 00005
          announce-email-to: dev@example.apache.org
          announce-subject: "[ANNOUNCE] Apache Example ${{ github.ref_name }} released"
          announce-body: |
            The Apache Example team is pleased to announce...
          announce-path-suffix: example/${{ github.ref_name }}
```

## Further details

- The job must grant `id-token: write` so that this action can request a GitHub OIDC token, which the ATR validates via JWKS. The OIDC token determines which ATR project is being updated.
- The ATR host must match `*.apache.org`, otherwise the workflow will fail.
