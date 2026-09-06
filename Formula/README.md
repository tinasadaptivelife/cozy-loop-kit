# Homebrew formula

This repo doubles as its own Homebrew tap — any repo with a `Formula/`
directory works as one.

## Install

```bash
brew tap tinasadaptivelife/cozy-loop-kit https://github.com/tinasadaptivelife/cozy-loop-kit
brew install cozyloop
```

Until `v0.1.0` is tagged (see below), install the tip of `main`:

```bash
brew install --HEAD cozyloop
```

`brew` pulls in `ffmpeg` (which provides `ffprobe` too) and builds cozyloop
into its own Python virtualenv. There are no other dependencies.

## Cutting a release

The stable spec in [`cozyloop.rb`](cozyloop.rb) points at a GitHub release
tarball and carries a placeholder `sha256`. To make it real:

```bash
git tag v0.1.0
git push origin v0.1.0
curl -sL https://github.com/tinasadaptivelife/cozy-loop-kit/archive/refs/tags/v0.1.0.tar.gz \
  | shasum -a 256
```

Paste the digest into `sha256`, keep `version` in step with
`src/cozyloop/__init__.py`, then:

```bash
brew audit --strict --online Formula/cozyloop.rb
brew install --build-from-source Formula/cozyloop.rb
brew test cozyloop
```

## MCP server

The formula installs `cozyloop` only. `cozyloop-mcp` also lands on `PATH` but
needs the MCP SDK, which isn't vendored — `brew` reminds you in its caveats.
Add it to the formula's virtualenv, or use `pipx install "cozy-loop-kit[mcp]"`.
