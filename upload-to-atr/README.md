# Upload to ATR with GitHub OIDC and rsync

```
apache/tooling-actions/upload-to-atr
```

This composite GitHub Action registers a short lived SSH key with the ATR and then rsyncs a local directory to ATR at `/<project>/<version>/`. Use it to publish build artifacts to ATR without long lived credentials, as part of the [ATR Trusted Publishing](https://releases.apache.org/docs/trusted-publishing) workflow.

Status: PRODUCTION

## Inputs

- **project (required)**: Project name segment in the remote path.
- **version (required)**: Version segment in the remote path. This is the ATR version name, which may only contain letters, numbers, `+`, `.` and `-`, so a git ref such as `rel/1.2.3` can't be passed through directly.
- **src**: Local directory to upload. Default: `dist`. A trailing slash will be added automatically if omitted.
- **atr-host**: ATR host to upload to. Must be an `apache.org` host. Default: `releases.apache.org`.
- **ssh-port**: SSH port on ATR. Default: `2222`.
- **source-commit**: Full 40 character hash of the commit that the upload was built from. Default: `HEAD` of the checkout in `$GITHUB_WORKSPACE`, if that is a checkout of the repository running the workflow, and otherwise nothing.

## Example workflow

The `id-token` write permission is **required** when using this GitHub Action. Tagged versions of this action are not available. Replace `<COMMIT>` in this example with your chosen commit.

```yaml
name: Upload to ATR

on:
  workflow_dispatch:
    inputs:
      version:
        description: "Version to upload, e.g. 1.2.3-rc1"
        required: true

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

      # see https://infra.apache.org/release-signing.html#automated-release-signing
      - name: Sign artifacts
        run: |
          ./sign.sh

      - name: Upload to ATR
        uses: apache/tooling-actions/upload-to-atr@<COMMIT>
        with:
          project: example
          version: ${{ inputs.version }}
```

## Further details

The job must grant `id-token: write` so that this action can request a GitHub OIDC token.

This action generates an ephemeral Ed25519 SSH key, registers its public key with ATR using the GitHub JWT, which is checked used JWKS, and discards the key after the job. SSH uses `StrictHostKeyChecking=accept-new` so that the host key is learned on first connection.

The remote path is `/<project>/<version>/`. The contents of `src` are synced to ATR. ATR will create a new revision of the project with the synced files. If `rsync` is missing on the runner, this action installs it.

ATR records the commit that the workflow was triggered on, from the signed GitHub JWT. A workflow can check out a different commit, for example by passing `ref` to `actions/checkout`, so this action also declares the commit that was actually checked out and ATR uses that as the release's source commit. ATR compares source archives against a clone of the repository at that commit, which is how a wrong declaration would be caught. If the workflow checks out the source somewhere other than `$GITHUB_WORKSPACE`, pass `source-commit` explicitly.
