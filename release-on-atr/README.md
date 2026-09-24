# Release on ATR using a GitHub OIDC JWT

```
apache/tooling-actions/release-on-atr
```

This composite GitHub Action resolves the vote on a release candidate, announces a release, or both, on ATR. It authenticates with a GitHub OIDC token, so no long lived credentials are needed, as part of the [ATR Trusted Publishing](https://releases.apache.org/docs/trusted-publishing) workflow.

Status: PRODUCTION

## Inputs

- **version (required)**: The ATR version name of the release, e.g. `1.2.3`. This may only contain letters, numbers, `+`, `.` and `-`, so a git ref such as `rel/1.2.3` can't be passed through directly.
- **atr-host**: ATR host. Must be an `apache.org` host. Default: `releases.apache.org`.
- **resolve**: `true` to resolve the vote. Default: `false`.
- **resolve-resolution**: `passed`, `failed` or `cancelled`. Required when `resolve` is `true`.
- **announce**: `true` to announce the release. Default: `false`.
- **announce-email-to**: Announcement recipient mailing list address. Required when `announce` is `true`. This must be one of the addresses that the project is permitted to announce to.
- **announce-body**: Announcement email body. Required when `announce` is `true`.

At least one of `resolve` and `announce` must be `true`. The action checks all of its inputs before it requests an OIDC token, so a mistake in the inputs fails the job before anything is sent to ATR.

## Release policy

ATR only accepts these calls from workflows that are listed in the project's release policy. Resolving a vote uses the list of vote workflow paths, and announcing a release uses the list of finish workflow paths. A workflow that does both must be in both lists. If the workflow is missing, the call fails with `Release policy for repository ... not found`.

The project must also be in a committee that is permitted to make automated releases.

If the release policy maps files to distribution platforms, those distributions must be recorded before the release can be announced, for example with [record-atr-distribution](../record-atr-distribution).

## Example workflows

The `id-token` write permission is **required** when using this GitHub Action. Tagged versions of this action are not available. Replace `<COMMIT>` in these examples with your chosen commit.

Resolve only:

```yaml
name: Resolve vote on ATR

on:
  workflow_dispatch:
    inputs:
      version:
        description: "Version to resolve, e.g. 1.2.3"
        required: true
      resolution:
        description: "Vote resolution"
        type: choice
        options: [passed, failed, cancelled]

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
          version: ${{ inputs.version }}
          resolve: "true"
          resolve-resolution: ${{ inputs.resolution }}
```

Announce only:

```yaml
name: Announce release on ATR

on:
  workflow_dispatch:
    inputs:
      version:
        description: "Version to announce, e.g. 1.2.3"
        required: true

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
          version: ${{ inputs.version }}
          announce: "true"
          announce-email-to: announce@apache.org
          announce-body: |
            The Apache Example team is pleased to announce...
```

Resolve then announce in one job:

```yaml
name: Resolve and announce on ATR

on:
  workflow_dispatch:
    inputs:
      version:
        description: "Version to release, e.g. 1.2.3"
        required: true

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
          version: ${{ inputs.version }}
          resolve: "true"
          resolve-resolution: passed
          announce: "true"
          announce-email-to: announce@apache.org
          announce-body: |
            The Apache Example team is pleased to announce...
```

This doesn't work for podlings. When a podling's first round vote passes, ATR starts the second round vote, and the release can't be announced until that has been resolved too.

## Further details

The job must grant `id-token: write` so that this action can request a GitHub OIDC token, which ATR checks using JWKS. The workflow's repository and path in the token decide which ATR project is being updated.

ATR announces the revision that was voted on, because nothing can be added to a release once its vote has started. This action does not send a commit hash, because the source commit of a release is recorded when it is uploaded, by [upload-to-atr](../upload-to-atr).

The announcement recipient address is masked in the workflow log.
