"""Song Loop Short: one song, played once, over vertical scenery cut to its sections.

    cozyloop short river-knows.short.json            # cards, cover and the video
    cozyloop short river-knows.short.json --cards    # cards and cover only (fast, to review)
    cozyloop short river-knows.short.json --sheet    # 5-frame contact sheet of every clip

Everything is described by one JSON spec (see examples/river-knows.short.json):

  song            the track, played once from 0:00
  song_end        seconds where the scenery hands over to the end card (default: song length)
  clips_root      folder the timeline's clip paths are relative to (optional)
  timeline        [[start_s, "clip.mp4"], [start_s, "clip.mp4", in_point_s], ...]; each clip plays
                  from its start to the next start. An in-point skips a title a generator baked
                  into the first seconds. Cut starts on the song's sections (verse, chorus...).
  bed             ambience files (e.g. a river), each set to bed_lufs by a fixed gain, crossfaded end
                  to end under everything; bed_level scales it. For Woonsocket use the one steady
                  river (SFX/thewoonsocketwonders/AMBIENCE-_Gentle_River_Flowing.mp3) kept faint:
                  bed_lufs -37, bed_level 0.8 (~25 dB under a -14 LUFS song)
  intro           opening card over the first seconds: {kicker, title, lines[], seconds} or {image}
  end_card        {kicker, title, label, lines[], art, seconds} or {image, seconds}
  cover           {frame: clip, t, kicker, title, label} -> <out>.cover.jpg (custom thumbnail)
  look            fonts and colours for the cards (the xil-microclips Woonsocket look by default
                  keys: show_name, fonts{display_bold, display_italic, body_bold}, colors{...})

The video is 1080x1920 30 fps H.264 + AAC 48 kHz, two-pass loudness to -14 LUFS / -1 dBTP (the
YouTube Shorts numbers xil-microclips' `series finalize` uses). No captions are burned in: ship
the lyrics as a separate .srt for YouTube closed captions.

Cards need Pillow (`pip install pillow`); the video itself needs only ffmpeg.
"""

import json
import os
import re
import subprocess
import sys

W, H = 1080, 1920
SAFE_L = 110                      # left/right margin clear of the Shorts like/comment rail

DEFAULT_LOOK = {                  # The Woonsocket Wonders microclips look (cream card, Playfair)
    "show_name": "The Woonsocket Wonders",
    "fonts": {
        "display_bold": "~/projects/the-woonsocket-wonders/brand/fonts/PlayfairDisplay-700.woff2",
        "display_italic": "~/projects/the-woonsocket-wonders/brand/fonts/PlayfairDisplay-500i.woff2",
        "body_bold": "~/projects/the-woonsocket-wonders/brand/fonts/Quicksand-700.woff2",
    },
    "colors": {"bg": "#F5EBE0", "ink": "#4A4A4A", "kicker": "#8E4E40", "label_ink": "#3F6B66"},
}


def _x(p):
    return os.path.expanduser(p) if isinstance(p, str) else p


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-3000:])
        raise SystemExit(f"error: {cmd[0]} failed ({p.returncode})")
    return p.stderr


def _dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          path], capture_output=True, text=True).stdout.strip()
    return float(out)


class Spec:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        d = json.load(open(self.path))
        self.d = d
        rel = lambda p: _x(p) if os.path.isabs(_x(p)) else os.path.join(self.dir, p)
        self.out = rel(d.get("out", os.path.splitext(os.path.basename(path))[0] + ".mp4"))
        self.work = rel(d.get("work", os.path.splitext(self.out)[0] + "_work"))
        self.song = _x(d["song"])
        self.song_end = float(d.get("song_end") or _dur(self.song))
        root = _x(d.get("clips_root", self.dir))
        self.timeline = [(float(t[0]), os.path.join(root, t[1]), float(t[2]) if len(t) > 2 else 0.0)
                         for t in d["timeline"]]
        self.bed = [_x(b) for b in d.get("bed", [])]
        self.bed_level = float(d.get("bed_level", 1.4))
        self.bed_lufs = float(d.get("bed_lufs", -30))
        self.xfade = float(d.get("xfade", 1.0))
        self.fps = int(d.get("fps", 30))
        self.intro = d.get("intro", {})
        self.end = d.get("end_card", {})
        self.cover = d.get("cover")
        self.loudness = float(d.get("loudness", -14))
        self.true_peak = float(d.get("true_peak", -1))
        look = json.loads(json.dumps(DEFAULT_LOOK))
        for k, v in d.get("look", {}).items():
            look[k] = {**look[k], **v} if isinstance(v, dict) else v
        self.look = look
        self.end_seconds = float(self.end.get("seconds", 5.0))
        self.intro_seconds = float(self.intro.get("seconds", 4.5))
        self.total = self.song_end + self.end_seconds
        self.clips_root = root

    def check(self):
        """Every clip exists and is long enough for its slot (plus the crossfade and in-point)."""
        errs = []
        for i, (start, clip, ss) in enumerate(self.timeline):
            if not os.path.exists(clip):
                errs.append(f"missing clip: {clip}")
                continue
            nxt = self.timeline[i + 1][0] if i + 1 < len(self.timeline) else self.song_end
            if nxt <= start:
                errs.append(f"timeline not increasing at {start}")
            need = ss + (nxt - start) + self.xfade
            have = _dur(clip)
            if need > have + 0.02:
                errs.append(f"{os.path.basename(clip)} at {start:.1f}s needs {need:.2f}s, has {have:.2f}s "
                            f"(shorten its slot or add a clip)")
        for b in self.bed + [self.song]:
            if not os.path.exists(b):
                errs.append(f"missing audio: {b}")
        if self.total > 180:
            print(f"  note: {self.total:.0f}s is over the 3-minute Shorts limit; it will post as a regular video")
        if errs:
            raise SystemExit("error: " + "\n       ".join(errs))


# ------------------------------------------------------------------ cards (Pillow)

class Look:
    def __init__(self, look):
        try:
            from PIL import ImageFont
        except ImportError:
            raise SystemExit("error: cards need Pillow: pip install pillow (or pass image: PNGs instead)")
        f, self.c, self.show = look["fonts"], look["colors"], look["show_name"]

        def font(key, size, weight):
            ft = ImageFont.truetype(_x(f[key]), size)
            try:
                ft.set_variation_by_axes([weight])
            except Exception:
                pass
            return ft
        self.title = font("display_bold", 96, 700)
        self.hook = font("display_italic", 66, 500)
        self.kicker = font("body_bold", 40, 700)
        self.body = font("body_bold", 38, 600)


def _rgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def _wrap(d, text, font, max_w):
    rows, cur = [], []
    for w in text.split():
        if cur and d.textlength(" ".join(cur + [w]), font=font) > max_w:
            rows.append(" ".join(cur)); cur = [w]
        else:
            cur.append(w)
    return rows + ([" ".join(cur)] if cur else [])


def _panel(d, lk, top, kicker, title, lines, first_accent=2):
    """Centred cream panel: kicker, big title, body lines (first `first_accent` in the label colour)."""
    L, R = SAFE_L, W - SAFE_L
    rows = _wrap(d, title, lk.title, R - L)
    h = 50 + 70 + 108 * len(rows) + 30 + 56 * len(lines) + 40
    d.rounded_rectangle((L - 40, top, R + 40, top + h), 44, fill=_rgb(lk.c["bg"], 240))
    y = top + 50

    def centre(text, font, colour):
        d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=_rgb(colour))
    centre(kicker.upper(), lk.kicker, lk.c["kicker"]); y += 70
    for r in rows:
        centre(r, lk.title, lk.c["ink"]); y += 108
    y += 30
    for i, ln in enumerate(lines):
        centre(ln, lk.body, lk.c["label_ink"] if i < first_accent else lk.c["ink"]); y += 56


def intro_overlay(spec, lk, path):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    i = spec.intro
    _panel(ImageDraw.Draw(img), lk, int(i.get("top", 330)), i["kicker"], i["title"], i.get("lines", []),
           int(i.get("accent_lines", 2)))
    img.save(path)
    return path


def end_card(spec, lk, path):
    """xil-microclips 'full episode' end card: rounded art box, kicker, title, show + label, lines."""
    from PIL import Image, ImageDraw
    e = spec.end
    img = Image.new("RGB", (W, H), _rgb(lk.c["bg"])[:3])
    d = ImageDraw.Draw(img)
    art = e.get("art")
    if art:
        art = art if os.path.isabs(_x(art)) else os.path.join(spec.clips_root, art)
        a = Image.open(_x(art)).convert("RGB")
        bw, bh, m, top = W - 180, 780, 90, 200
        s = max(bw / a.width, bh / a.height)
        a = a.resize((int(a.width * s), int(a.height * s)))
        a = a.crop(((a.width - bw) // 2, (a.height - bh) // 2, (a.width + bw) // 2, (a.height + bh) // 2))
        mask = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), 40, fill=255)
        img.paste(a, (m, top), mask)
    x, y, maxw = 90, 1060, W - 180
    d.text((x, y), e["kicker"].upper(), font=lk.kicker, fill=_rgb(lk.c["kicker"])); y += 70
    for r in _wrap(d, e["title"], lk.title, maxw):
        d.text((x, y), r, font=lk.title, fill=_rgb(lk.c["ink"])); y += 108
    y += 24
    for text, gap in ((lk.show, 52), (e.get("label", ""), 70)):
        if text:
            d.text((x, y), text, font=lk.body, fill=_rgb(lk.c["label_ink"])); y += gap
    for ln in e.get("lines", []):
        for r in _wrap(d, ln, lk.body, maxw):
            d.text((x, y), r, font=lk.body, fill=_rgb(lk.c["ink"])); y += 56
    img.save(path)
    return path


def grab(clip, t, path):
    _run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", clip, "-frames:v", "1",
          "-vf", f"scale={W}:{H}:flags=lanczos", path])
    return path


def cover(spec, lk, path):
    """1080x1920 custom thumbnail: a scenery frame with the cream title panel mid-frame."""
    from PIL import Image, ImageDraw
    c = spec.cover
    frame = c["frame"] if os.path.isabs(_x(c["frame"])) else os.path.join(spec.clips_root, c["frame"])
    img = Image.open(grab(_x(frame), float(c.get("t", 5)), os.path.join(spec.work, "cover_bg.png"))).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    rows = _wrap(d, c["title"], lk.title, W - 2 * SAFE_L)
    h = 70 + 70 + 108 * len(rows) + 30 + 52 + 60
    top = int(H * 0.52) - h // 2
    d.rounded_rectangle((SAFE_L - 40, top, W - SAFE_L + 40, top + h), 44, fill=_rgb(lk.c["bg"], 240))
    y = top + 50
    for text, font, col, adv in [(c["kicker"].upper(), lk.kicker, lk.c["kicker"], 70)] + \
            [(r, lk.title, lk.c["ink"], 108) for r in rows]:
        d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=_rgb(col)); y += adv
    y += 30
    t = f"{lk.show}  ·  {c.get('label', '')}".rstrip(" ·")
    d.text(((W - d.textlength(t, font=lk.body)) / 2, y), t, font=lk.body, fill=_rgb(lk.c["label_ink"]))
    img.save(path, quality=92)
    return path


def contact_sheet(spec, path):
    """Five frames per clip (0.2 s, 1.5 s, middle, late, end): generators fade titles out in the
    first ~2.5 s, so a single mid-clip frame misses them."""
    from PIL import Image, ImageDraw
    tw, th = 135, 240
    rows = []
    for i, (start, clip, ss) in enumerate(spec.timeline):
        d = _dur(clip)
        row = Image.new("RGB", (5 * tw, th))
        for k, t in enumerate([0.2, 1.5, d / 2, d * 0.75, d - 0.3]):
            p = os.path.join(spec.work, f"sheet_{i}_{k}.jpg")
            _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", clip, "-frames:v", "1",
                  "-vf", f"scale={tw}:{th}", p])
            row.paste(Image.open(p), (k * tw, 0))
        dr = ImageDraw.Draw(row)
        dr.rectangle([0, 0, 64, 24], fill="black")
        dr.text((4, 4), f"{i} {int(start // 60)}:{int(start % 60):02d}", fill="white")
        rows.append(row)
    sheet = Image.new("RGB", (2 * 5 * tw + 10, ((len(rows) + 1) // 2) * th))
    for j, r in enumerate(rows):
        sheet.paste(r, ((j % 2) * (5 * tw + 10), (j // 2) * th))
    sheet.save(path, quality=85)
    return path


# ------------------------------------------------------------------ audio + video

def _lufs(path):
    err = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    v = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(v[-1]) if v else spec_default_lufs


spec_default_lufs = -30.0


def bed(spec, path, xf=2.0):
    """The ambience files, each set to bed_lufs with one fixed gain (no dynamic loudnorm, which
    pumps on short files), cycled and crossfaded end to end until the video is covered, so a 10 s
    river loops with no hard seam."""
    gains = {f: spec.bed_lufs - _lufs(f) for f in dict.fromkeys(spec.bed)}
    durs = {f: _dur(f) for f in gains}
    seq, have = [], 0.0
    while have < spec.total + 1 or not seq:
        f = spec.bed[len(seq) % len(spec.bed)]
        have += durs[f] - (xf if seq else 0)
        seq.append(f)
    ins, parts = [], []
    for i, f in enumerate(seq):
        ins += ["-i", f]
        parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={gains[f]:.2f}dB[r{i}]")
    chain, last = [], "r0"
    for i in range(1, len(seq)):
        chain.append(f"[{last}][r{i}]acrossfade=d={xf}:c1=qsin:c2=qsin[x{i}]"); last = f"x{i}"
    _run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(parts + chain),
          "-map", f"[{last}]", "-t", str(spec.total + 1), path])
    return path


def video(spec, intro_png, end_png, bed_wav):
    ins, f, n, XF = [], [], len(spec.timeline), spec.xfade
    for i, (start, clip, ss) in enumerate(spec.timeline):
        nxt = spec.timeline[i + 1][0] if i + 1 < n else spec.song_end
        dur = nxt - start + XF
        ins += ["-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", clip]
        f.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
                 f"setsar=1,fps={spec.fps},format=yuv420p,trim=duration={dur:.3f},setpts=PTS-STARTPTS[c{i}]")
    ins += ["-loop", "1", "-t", f"{spec.end_seconds + XF:.3f}", "-i", end_png]
    f.append(f"[{n}:v]scale={W}:{H},setsar=1,fps={spec.fps},format=yuv420p[c{n}]")
    last = "c0"
    for i in range(1, n + 1):
        off = spec.timeline[i][0] if i < n else spec.song_end
        f.append(f"[{last}][c{i}]xfade=transition=fade:duration={XF}:offset={off:.3f}[v{i}]"); last = f"v{i}"
    k = n + 1
    if intro_png:
        s = spec.intro_seconds
        ins += ["-loop", "1", "-t", str(s + 1), "-i", intro_png]
        f.append(f"[{k}:v]format=rgba,fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st={s - 0.6}:d=0.6:alpha=1[ov]")
        f.append(f"[{last}][ov]overlay=0:0:eof_action=pass,trim=duration={spec.total},format=yuv420p[vout]")
        k += 1
    else:
        f.append(f"[{last}]trim=duration={spec.total},format=yuv420p[vout]")
    ins += ["-i", spec.song]
    f.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={spec.total}[song]")
    if bed_wav:
        ins += ["-i", bed_wav]
        f.append(f"[{k + 1}:a]atrim=duration={spec.total},volume={spec.bed_level},afade=t=in:d=1.5,"
                 f"afade=t=out:st={spec.total - 3}:d=3[bed]")
        f.append("[song][bed]amix=inputs=2:normalize=0:duration=first[aout]")
    else:
        f.append(f"[song]afade=t=out:st={spec.total - 3}:d=3[aout]")
    mixed = os.path.join(spec.work, "mixed.mp4")
    print(f"  rendering {len(spec.timeline)} clips, {spec.total:.1f}s ...", flush=True)
    _run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(f), "-map", "[vout]", "-map", "[aout]",
          "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
          "-r", str(spec.fps), "-c:a", "pcm_s16le", "-t", str(spec.total), mixed])
    loudnorm(mixed, spec.out, spec.loudness, spec.true_peak)


def loudnorm(src, dst, I=-14.0, TP=-1.0):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af",
                          f"loudnorm=I={I}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err).group(0))
    af = (f"loudnorm=I={I}:TP={TP}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
          "linear=true,aresample=48000")
    _run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af", af,
          "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", dst])


def report(path):
    err = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    print(f"  {os.path.basename(path)}: {_dur(path):.1f}s, {i[-1] if i else '?'} LUFS, "
          f"true peak {pk[-1] if pk else '?'} dBFS")


def cmd_short(a):
    spec = Spec(a.spec)
    os.makedirs(spec.work, exist_ok=True)
    spec.check()
    stem = os.path.splitext(spec.out)[0]
    if a.sheet:
        print("  wrote", contact_sheet(spec, stem + ".sheet.jpg"))
        return
    needs_look = ("image" not in spec.intro and spec.intro) or "image" not in spec.end or spec.cover
    lk = Look(spec.look) if needs_look else None
    intro_png = None
    if spec.intro:
        intro_png = _x(spec.intro["image"]) if "image" in spec.intro else \
            intro_overlay(spec, lk, os.path.join(spec.work, "intro_overlay.png"))
    end_png = _x(spec.end["image"]) if "image" in spec.end else end_card(spec, lk, stem + ".end_card.png")
    if spec.cover:
        print("  wrote", cover(spec, lk, stem + ".cover.jpg"))
    if intro_png and "image" not in spec.intro:
        from PIL import Image
        bg = Image.open(grab(spec.timeline[0][1], 1.0, os.path.join(spec.work, "intro_bg.png"))).convert("RGBA")
        Image.alpha_composite(bg, Image.open(intro_png)).convert("RGB").save(stem + ".intro_preview.jpg", quality=90)
        print("  wrote", stem + ".intro_preview.jpg")
    if a.cards:
        return
    bed_wav = bed(spec, os.path.join(spec.work, "bed.wav")) if spec.bed else None
    video(spec, intro_png, end_png, bed_wav)
    report(spec.out)
    print("  wrote", spec.out)


def add_parser(sub):
    s = sub.add_parser("short", help="Song Loop Short: one song over vertical scenery cut to its sections")
    s.add_argument("spec", help="JSON spec (see examples/river-knows.short.json)")
    s.add_argument("--cards", action="store_true", help="cards, cover and intro preview only")
    s.add_argument("--sheet", action="store_true", help="5-frame contact sheet of every timeline clip")
    s.set_defaults(func=cmd_short)
