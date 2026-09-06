# Homebrew formula

This repo doubles as its own Homebrew tap — any repo with a `Formula/`
directory works as one.

## Install

```bash
brew tap tinasadaptivelife/cozy-loop-kit https://github.com/tinasadaptivelife/cozy-loop-kit
brew install cozyloop
```

`brew install --HEAD cozyloop` builds the tip of `main` instead of the
tagged release.

`brew` pulls in `ffmpeg` (which provides `ffprobe` too) and builds cozyloop
into its own Python virtualenv. There are no other dependencies.

## Cutting a release

The stable spec in [`cozyloop.rb`](cozyloop.rb) points at a GitHub tag
tarball. `v0.1.0` is tagged; for the next one:

```bash
git tag v0.2.0
git push origin v0.2.0
curl -sL https://github.com/tinasadaptivelife/cozy-loop-kit/archive/refs/tags/v0.2.0.tar.gz \
  | shasum -a 256
```

Update `url`, `version`, and `sha256` in the formula, keeping `version` in
step with `src/cozyloop/__init__.py`, then:

```bash
brew audit --strict --online --tap tinasadaptivelife/cozy-loop-kit cozyloop
brew install cozyloop
brew test cozyloop
```

## MCP server

The formula installs `cozyloop` only. `cozyloop-mcp` also lands on `PATH` but
needs the MCP SDK, which isn't vendored — `brew` reminds you in its caveats.
Add it to the formula's virtualenv, or use `pipx install "cozy-loop-kit[mcp]"`.
