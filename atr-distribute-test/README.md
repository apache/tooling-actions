# Download from ATR and distribute

```
apache/tooling-actions/atr-distribute-test
```

This composite GitHub Action registers a short lived SSH key with the ATR and then rsyncs the release contents to the github runner. Use it to pull build artifacts from ATR without long lived credentials.

Status: EXPERIMENTAL

## Inputs

- **project (required)**: Project name segment in the remote path.
- **version (required)**: Version segment in the remote path.
- **src**: Local directory to upload. Default: `dist`. A trailing slash will be added automatically if omitted.
- **atr-host**: ATR host to upload to. Default: `release-test.apache.org`.
- **ssh-port**: SSH port on ATR. Default: `2222`.

## Example workflow

The `id-token` write permission is **required** when using this GitHub Action. Tagged versions of this action are not available. Replace `<COMMIT>` in this example with your chosen commit.

This action was designed to be run by workflows in *this* repository.

```yaml
name: Distribute from ATR
run-name: "${{ inputs.id }}"

on:
  workflow_dispatch:
    inputs:
      id:
        description: 'Test run ID'
        required: true
      platform:
        description: 'Distribution platform'
        required: true
      distribution-package:
        description: 'Package/project name in ATR'
        required: true
      version:
        description: 'Version in ATR to pull files from'
        required: true
      distribution-version:
        description: 'Distribution version'
        required: true

jobs:
  upload:
    permissions:
      id-token: write
      contents: read
    runs-on: ubuntu-latest
    steps:
      - name: Distribute from ATR
        uses: apache/tooling-actions/atr-distribute-test@<COMMIT>
        with:
          platform: ${{ inputs.platform }}
          distribution-package: ${{ inputs.distribution-package }}
          version: ${{ inputs.version }}
          distribution-version: ${{ inputs.distribution-version }}
```

## Further details

The job must grant `id-token: write` so that this action can request a GitHub OIDC token.

This action generates an ephemeral Ed25519 SSH key, registers its public key with ATR using the GitHub JWT, which is checked used JWKS, and discards the key after the job. SSH uses `StrictHostKeyChecking=accept-new` so that the host key is learned on first connection.

The remote path is `/<project>/<version>/`. The contents are synced from ATR to the runner. If `rsync` is missing on the runner, this action installs it.
