"""MCP server exposing cozyloop as tools.

    cozyloop-mcp        # stdio transport, for Claude Desktop / Claude Code

Needs the MCP SDK:  pip install 'cozyloop[mcp]'  (or  pipx inject cozyloop mcp)

cozyloop prints progress to stdout, which would corrupt the stdio JSON-RPC
stream, so every render runs as a subprocess (`python -m cozyloop ...`) with its
output captured to a per-job log file rather than being called in-process.
Renders are slow — a multi-hour video is ~8 min of encoding — so `build` and
`render_ambience` are background jobs: they return a job record, and with
wait=True (the default) block until the job finishes or `timeout_s` elapses,
after which you poll `job_status`.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

# Per-job scratch (logs, meta, and each build's own --work dir so concurrent
# builds never share an output directory). Override with COZYLOOP_MCP_JOBS.
JOBS_ROOT = Path(os.environ.get("COZYLOOP_MCP_JOBS")
                 or Path(tempfile.gettempdir()) / "cozyloop-mcp-jobs")

_procs: "dict[str, subprocess.Popen]" = {}


def _now() -> float:
    return time.time()


def _job_dir(job_id: str) -> Path:
    return JOBS_ROOT / job_id


def _read_meta(job_id: str) -> dict:
    p = _job_dir(job_id) / "meta.json"
    if not p.exists():
        raise ValueError(f"unknown job {job_id!r}")
    return json.loads(p.read_text())


def _write_meta(job_id: str, meta: dict) -> None:
    (_job_dir(job_id) / "meta.json").write_text(json.dumps(meta, indent=2))


def _tail(path: Path, n: int = 40) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(errors="replace").splitlines()[-n:])


def _expand(paths) -> "list[str]":
    return [os.path.abspath(os.path.expanduser(p)) for p in (paths or [])]


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _spawn(kind: str, cli_args: "list[str]", out: str) -> str:
    job_id = f"{kind}-{uuid.uuid4().hex[:8]}"
    jd = _job_dir(job_id)
    jd.mkdir(parents=True, exist_ok=True)
    work = str(jd / "work")
    if kind == "build" and "--work" not in cli_args:
        cli_args = [*cli_args, "--work", work]
    log = jd / "log.txt"
    cmd = [sys.executable, "-m", "cozyloop", *cli_args]
    _write_meta(job_id, {
        "job_id": job_id, "kind": kind, "cmd": cmd, "pid": None,
        "out": os.path.abspath(out), "log": str(log), "work": work,
        "started": _now(), "ended": None, "returncode": None,
    })
    lf = open(log, "w")
    try:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                cwd=str(jd), start_new_session=True)
    finally:
        lf.close()
    _procs[job_id] = proc
    meta = _read_meta(job_id)
    meta["pid"] = proc.pid
    _write_meta(job_id, meta)
    return job_id


def _poll(job_id: str) -> dict:
    meta = _read_meta(job_id)
    rc = meta.get("returncode")
    running = False
    if rc is None:
        proc = _procs.get(job_id)
        if proc is not None:
            rc = proc.poll()
            running = rc is None
        elif meta.get("pid") and _alive(meta["pid"]):
            running = True
        if rc is not None:
            meta["returncode"] = rc
            meta["ended"] = _now()
            _write_meta(job_id, meta)
            _procs.pop(job_id, None)
    out = Path(meta["out"])
    if running:
        state = "running"
    elif rc == 0:
        state = "succeeded"
    elif rc is not None:
        state = "failed"
    else:  # orphaned by a server restart, no exit code recorded
        state = "succeeded" if out.exists() else "failed"
    return {
        "job_id": job_id,
        "kind": meta["kind"],
        "state": state,
        "returncode": rc,
        "started": meta["started"],
        "elapsed_s": round((meta.get("ended") or _now()) - meta["started"], 1),
        "output": meta["out"],
        "output_exists": out.exists(),
        "output_size_mb": round(out.stat().st_size / 1e6, 1) if out.exists() else 0,
        "work_dir": meta["work"],
        "log_tail": _tail(Path(meta["log"])),
    }


def _wait(job_id: str, timeout_s: float) -> dict:
    deadline = _now() + max(0.0, timeout_s)
    st = _poll(job_id)
    while st["state"] == "running" and _now() < deadline:
        time.sleep(2.0)
        st = _poll(job_id)
    if st["state"] == "running":
        st["note"] = (f"still running after {timeout_s:g}s — call "
                      f"job_status('{job_id}') later, or re-run with a larger "
                      f"timeout_s")
    return st


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------

def list_presets() -> str:
    """List the built-in ambience presets and every layer name you can pass in
    the `layers` argument (as "name", "name:level", or "name:key=val,key=val")."""
    from cozyloop import ambience
    out = ["PRESETS"]
    for k, v in ambience.PRESETS.items():
        names = ", ".join(n for n, _ in v["layers"])
        out.append(f"\n  {k}\n    {v['desc']}\n    layers: {names}")
    out.append("\n\nLAYERS")
    out.append("  " + ", ".join(sorted(ambience.LAYERS)))
    return "\n".join(out)


def build(
    clips: "list[str]",
    out: str,
    duration: str = "2h",
    preset: "str | None" = None,
    keep_source_audio: bool = False,
    source_audio_level: float = 0.7,
    music: "list[str] | None" = None,
    music_level: float = 0.55,
    music_xfade: float = 6.0,
    sfx: "list[str] | None" = None,
    sfx_level: float = 0.8,
    layers: "list[str] | None" = None,
    fade: float = 1.0,
    size: "str | None" = None,
    fps: "float | None" = None,
    crf: "int | None" = None,
    gain: "float | None" = None,
    target_lufs: float = -17.0,
    target_peak: float = -1.5,
    fade_in: float = 10.0,
    fade_out: float = 25.0,
    sync_thunder: bool = False,
    thunder_sfx: "str | None" = None,
    thunder_delay: float = 3.0,
    wait: bool = True,
    timeout_s: float = 1800.0,
) -> dict:
    """Build a finished long-form video from short clips plus an ambience bed
    (wraps `cozyloop build`).

    `clips` are files or directories. Leave `preset` unset to keep the clips'
    own audio (with `keep_source_audio=True`), to run music/sfx only, or to let
    cozyloop pick its default bed. Each job renders into its own work directory,
    so several builds can run at once without colliding.

    Returns a job record. With wait=True this blocks until the render finishes
    or `timeout_s` seconds pass; then use `job_status(job_id)`. The record's
    `log_tail` carries cozyloop's own [verify] report (duration, loudness, true
    peak, loop-seam delta, level spot-checks) once the job succeeds.
    """
    outp = os.path.abspath(os.path.expanduser(out))
    args = ["build", *_expand(clips), "-o", outp, "-d", str(duration)]
    if preset:
        args += ["--preset", preset]
    if keep_source_audio:
        args += ["--keep-source-audio",
                 "--source-audio-level", str(source_audio_level)]
    for m in _expand(music):
        args += ["--music", m]
    if music:
        args += ["--music-level", str(music_level), "--music-xfade", str(music_xfade)]
    for s in _expand(sfx):
        args += ["--sfx", s]
    if sfx:
        args += ["--sfx-level", str(sfx_level)]
    for spec in (layers or []):
        args += ["--layer", spec]
    args += ["--fade", str(fade)]
    if size:
        args += ["--size", size]
    if fps is not None:
        args += ["--fps", str(fps)]
    if crf is not None:
        args += ["--crf", str(crf)]
    if gain is not None:
        args += ["--gain", str(gain)]
    args += ["--target-lufs", str(target_lufs), "--target-peak", str(target_peak),
             "--fade-in", str(fade_in), "--fade-out", str(fade_out)]
    if sync_thunder:
        args.append("--sync-thunder")
    if thunder_sfx:
        args += ["--thunder-sfx", os.path.abspath(os.path.expanduser(thunder_sfx)),
                 "--thunder-delay", str(thunder_delay)]
    job_id = _spawn("build", args, outp)
    return _wait(job_id, timeout_s) if wait else _poll(job_id)


def render_ambience(
    out: str,
    duration: str = "90",
    preset: str = "rainy-shop",
    layers: "list[str] | None" = None,
    music: "list[str] | None" = None,
    music_level: float = 0.55,
    gain: "float | None" = None,
    target_lufs: float = -17.0,
    fade_in: float = 10.0,
    fade_out: float = 25.0,
    wait: bool = True,
    timeout_s: float = 900.0,
) -> dict:
    """Render an ambience bed on its own, no video (wraps `cozyloop audio`).
    Output extension picks the codec (.m4a/.wav/.flac/.mp3/...). Same job/wait
    semantics as `build`."""
    outp = os.path.abspath(os.path.expanduser(out))
    args = ["audio", "-o", outp, "-d", str(duration), "--preset", preset]
    for spec in (layers or []):
        args += ["--layer", spec]
    for m in _expand(music):
        args += ["--music", m]
    if music:
        args += ["--music-level", str(music_level)]
    if gain is not None:
        args += ["--gain", str(gain)]
    args += ["--target-lufs", str(target_lufs),
             "--fade-in", str(fade_in), "--fade-out", str(fade_out)]
    job_id = _spawn("audio", args, outp)
    return _wait(job_id, timeout_s) if wait else _poll(job_id)


def job_status(job_id: str, wait: bool = False, timeout_s: float = 600.0) -> dict:
    """Current state of a build/render job. wait=True blocks until it leaves the
    running state or `timeout_s` elapses."""
    return _wait(job_id, timeout_s) if wait else _poll(job_id)


def list_jobs() -> "list[dict]":
    """Every job this server has started (and any left in JOBS_ROOT), newest
    first."""
    if not JOBS_ROOT.exists():
        return []
    jobs = []
    for d in sorted(JOBS_ROOT.iterdir()):
        if (d / "meta.json").exists():
            try:
                jobs.append(_poll(d.name))
            except Exception:
                pass
    return sorted(jobs, key=lambda j: j["started"], reverse=True)


def cancel_job(job_id: str) -> dict:
    """Terminate a running job."""
    meta = _read_meta(job_id)
    proc = _procs.get(job_id)
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
    elif meta.get("pid") and _alive(meta["pid"]):
        try:
            os.killpg(os.getpgid(meta["pid"]), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    return _poll(job_id)


def verify(path: str) -> str:
    """Run cozyloop's verifier on a finished file — duration, integrated
    loudness, true peak, loop-seam delta, and level spot-checks through the
    file. Runs synchronously (up to ~1 min on a multi-hour render)."""
    p = os.path.abspath(os.path.expanduser(path))
    r = subprocess.run([sys.executable, "-m", "cozyloop", "verify", p],
                       capture_output=True, text=True, timeout=900)
    return (r.stdout + r.stderr).strip() or f"(cozyloop verify exited {r.returncode})"


_TOOLS = [list_presets, build, render_ambience,
          job_status, list_jobs, cancel_job, verify]


def _server_class():
    """The MCP server class, across SDK generations. FastMCP (mcp 1.x) was
    renamed MCPServer in mcp 2.x; the decorator/run surface we use is the
    same on both."""
    try:
        from mcp.server.mcpserver import MCPServer
        return MCPServer
    except ImportError:
        from mcp.server.fastmcp import FastMCP
        return FastMCP


def _make_app():
    app = _server_class()("cozyloop")
    for fn in _TOOLS:
        app.tool()(fn)
    return app


def main() -> None:
    try:
        _server_class()
    except ImportError:
        sys.stderr.write(
            "cozyloop-mcp needs the MCP SDK, which is an optional extra.\n"
            "  pipx:  pipx inject cozyloop 'mcp>=1.2'\n"
            "  pip :  pip install 'cozyloop[mcp]'\n")
        sys.exit(1)
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
    _make_app().run()


if __name__ == "__main__":
    main()
