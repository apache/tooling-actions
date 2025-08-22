### Upload to ATR with GitHub OIDC and rsync

This composite GitHub Action exchanges a GitHub OIDC token for an ATR JWT, registers a short lived SSH key, and rsyncs a local directory to ATR at `/<project>/<version>/`. Use it to publish build artifacts to ATR without long lived credentials.

Status: EXPERIMENTAL

### Inputs

- **asf-uid (required)**: Your ASF UID used for SSH login.
- **project (required)**: Project name segment in the remote path.
- **version (required)**: Version segment in the remote path.
- **src**: Local directory to upload. Default: `dist`. A trailing slash will be added automatically if omitted.
- **audience**: OIDC audience for the JWT request. Default: `atr-test`.
- **atr-host**: ATR host to upload to. Default: `release-test.apache.org`.
- **ssh-port**: SSH port on ATR. Default: `2222`.
- **rsync-args**: Arguments passed to `rsync`. Default: `-av`.

### Example workflow

The `id-token` write permission is **required** when using this GitHub Action.

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
      - uses: actions/checkout@v4

      - name: Build artifacts
        run: |
          ./build.sh

      - name: Upload to ATR
        uses: apache/tooling-actions/upload-to-atr@v1
        with:
          asf-uid: ${{ secrets.ASF_UID }}
          project: my-project
          version: ${{ github.ref_name }}
          src: dist
          audience: atr-test
          atr-host: release-test.apache.org
          ssh-port: '2222'
          rsync-args: -av
```

### Further details

The job must grant `id-token: write` so that this action can request a GitHub OIDC token.

This action generates an ephemeral Ed25519 SSH key, registers its public key with ATR using the GitHub JWT, which is checked used JWKS, and discards the key after the job. SSH uses `StrictHostKeyChecking=accept-new` so that the host key is learned on first connection.

The remote path is `/<project>/<version>/`. The contents of `src` are synced to ATR. ATR will create a new revision of the project with the synced files. If `rsync` is missing on the runner, this action installs it.

You should not adjust `rsync-args`, as ATR is very strict about which rsync arguments it accepts.
