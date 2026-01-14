# Upload to ATR with GitHub OIDC and rsync

```
apache/tooling-actions/upload-to-atr
```

This composite GitHub Action registers a short lived SSH key with the ATR and then rsyncs a local directory to ATR at `/<project>/<version>/`. Use it to publish build artifacts to ATR without long lived credentials.

Status: EXPERIMENTAL

## Inputs

- **project (required)**: Project name segment in the remote path.
- **version (required)**: Version segment in the remote path.
- **src**: Local directory to upload. Default: `dist`. A trailing slash will be added automatically if omitted.
- **atr-host**: ATR host to upload to. Default: `release-test.apache.org`.
- **ssh-port**: SSH port on ATR. Default: `2222`.

## Example workflow

The `id-token` write permission is **required** when using this GitHub Action. Tagged versions of this action are not available. Replace `<COMMIT>` in this example with your chosen commit.

```yaml
name: Upload to ATR

on:
  workflow_dispatch:

jobs:
  upload:
    permissions:
      id-token: write
      contents: read
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<COMMIT>

      - name: Build artifacts
        run: |
          ./build.sh

      - name: Upload to ATR
        uses: apache/tooling-actions/upload-to-atr@<COMMIT>
        with:
          project: example
          version: ${{ github.ref_name }}
```

## Further details

The job must grant `id-token: write` so that this action can request a GitHub OIDC token.

This action generates an ephemeral Ed25519 SSH key, registers its public key with ATR using the GitHub JWT, which is checked used JWKS, and discards the key after the job. SSH uses `StrictHostKeyChecking=accept-new` so that the host key is learned on first connection.

The remote path is `/<project>/<version>/`. The contents of `src` are synced to ATR. ATR will create a new revision of the project with the synced files. If `rsync` is missing on the runner, this action installs it.
