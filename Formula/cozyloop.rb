class Cozyloop < Formula
  include Language::Python::Virtualenv

  desc "Turn short generated clips into long-form sleep/lofi/cozy ambience videos"
  homepage "https://github.com/tinasadaptivelife/cozy-loop-kit"

  # Stable builds track tagged releases. To cut the next one:
  #   git tag vX.Y.Z && git push origin vX.Y.Z
  #   curl -sL https://github.com/tinasadaptivelife/cozy-loop-kit/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256
  # then update `url`, `version`, and `sha256`, keeping `version` in step with
  # src/cozyloop/__init__.py.
  url "https://github.com/tinasadaptivelife/cozy-loop-kit/archive/refs/tags/v0.1.0.tar.gz"
  version "0.1.0"
  sha256 "7fc1b8bc68ec7d1b93fdbd629bcd0591954edb305db90ea7f3a076230e46a8cc"
  license "MIT"
  head "https://github.com/tinasadaptivelife/cozy-loop-kit.git", branch: "main"

  depends_on "ffmpeg" # provides ffmpeg + ffprobe, required at runtime
  depends_on "python@3.13"

  # The base package has zero Python dependencies, so there are no `resource`
  # blocks to vendor — the virtualenv just holds cozyloop itself.
  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      cozyloop shells out to ffmpeg and ffprobe at runtime; both come from the
      "ffmpeg" formula installed as a dependency.

      The optional MCP server (cozyloop-mcp) needs the MCP SDK, which is not
      bundled here. Add it to this formula's virtualenv:
        #{libexec}/bin/pip install "mcp>=1.2"
      or install cozyloop with pipx instead, which supports the extra directly:
        pipx install "cozy-loop-kit[mcp]"
    EOS
  end

  test do
    assert_match(/cozyloop \d+\.\d+/, shell_output("#{bin}/cozyloop --version"))
    assert_match "rainy-shop", shell_output("#{bin}/cozyloop presets")
  end
end
