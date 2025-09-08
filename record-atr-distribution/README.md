# Record distribution on ATR using a GitHub OIDC JWT

```
apache/tooling-actions/record-atr-distribution
```

This composite GitHub Action records a distribution made on an external platform with ATR.

Status: EXPERIMENTAL

## Inputs

- **version (required)**: Release version (e.g. `1.2.3`).
- **platform (required)**: Distribution platform enum name (documented in the ATR API).
- **distribution-owner-namespace**: Owner namespace. Default: empty string.
- **distribution-package (required)**: Distribution package.
- **distribution-version (required)**: Distribution version.
- **staging**: If `"true"`, use staging. Default: `"false"`.
- **details**: If `"true"`, include detailed check. Default: `"false"`.
- **atr-host**: ATR host. Default: `release-test.apache.org`. Must match `*.apache.org`.

## Example workflow

The `id-token` write permission is required. Replace `<COMMIT>` with your chosen commit.

```yaml
name: Record distribution on ATR

on:
  workflow_dispatch:

jobs:
  record:
    permissions:
      id-token: write
      contents: read
    runs-on: ubuntu-latest
    steps:
      - name: Record distribution
        uses: apache/tooling-actions/record-atr-distribution@<COMMIT>
        with:
          version: ${{ github.ref_name }}
          platform: PYPI
          distribution-owner-namespace: ''
          distribution-package: example
          distribution-version: ${{ github.ref_name }}
          staging: "false"
          details: "false"
```

## Further details

- Job must grant `id-token: write` so the action can request a GitHub OIDC token.
- Host must match `*.apache.org`.
