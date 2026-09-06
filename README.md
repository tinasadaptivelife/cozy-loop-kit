# cozy-loop-kit

Turn a handful of short generated clips into a long-form sleep / lofi / cozy ambience video.
One command, no sample libraries, no licensing exposure.

```bash
cozyloop build ~/Downloads/my_clips --preset rainy-shop -d 2h -o video.mp4
```

Requires `ffmpeg` and `ffprobe` on PATH. No Python packages, no API keys, no network.

---

## Install

```bash
pipx install git+https://github.com/tinasadaptivelife/cozy-loop-kit
```

That puts `cozyloop` on your PATH in its own isolated environment. `pip install .`
from a clone works too. There are no Python dependencies — the only requirement is
`ffmpeg` and `ffprobe` on PATH (`brew install ffmpeg`); `cozyloop build` checks for
them and tells you if they're missing.

**Working from a clone without installing:** the repo-root `./cozyloop` script runs
straight from the checkout, so an existing symlink keeps working:

```bash
ln -s "$PWD/cozyloop" /opt/homebrew/bin/cozyloop
```

You can also run it as a module: `python -m cozyloop ...`.

---

## MCP server

`cozyloop-mcp` exposes the tool over the Model Context Protocol, so an assistant
can drive it directly instead of shell-scripting the CLI.

```bash
pipx install "git+https://github.com/tinasadaptivelife/cozy-loop-kit"
pipx inject cozyloop "mcp>=1.2"          # or: pip install "cozyloop[mcp]"
```

Register it (Claude Code):

```bash
claude mcp add cozyloop -- cozyloop-mcp
```

or in `claude_desktop_config.json`:

```json
{ "mcpServers": { "cozyloop": { "command": "cozyloop-mcp" } } }
```

**Tools:** `list_presets`, `build`, `render_ambience`, `job_status`, `list_jobs`,
`cancel_job`, `verify`. `build` and `render_ambience` run as background jobs —
they return a job record and, with `wait=true` (default), block until the render
finishes or `timeout_s` elapses, then you poll `job_status`. Each build gets its
own `--work` directory automatically, so concurrent jobs never collide. Job
scratch lives under the system temp dir (override with `COZYLOOP_MCP_JOBS`).

---

## What it does for you

Every step that was manual on the Franky video is now automatic:

| | |
|---|---|
| **Deduplicates clips** | Generators hand you the same file twice constantly. It md5s them and skips repeats, telling you which. |
| **Normalises mismatched clips** | Different sizes, framerates or aspect ratios get scaled and letterboxed to match clip 1 (or `--size` / `--fps`). |
| **Builds a seamless loop** | Crossfades every junction *including the wrap back to the start*, so tiling it 400 times is invisible. |
| **Proves the seam** | Measures the pixel delta between the loop's first and last frame and prints it. Under ~5/255 is imperceptible. |
| **Generates the audio** | One unbroken pass at full length, so the bed never repeats and there's no 30-second tell. |
| **Hits a loudness target** | Renders a probe, measures it, solves for the gain. Every preset lands at −17 LUFS without you touching a fader. |
| **Loops your music seamlessly** | Folds a track's tail over its own head with an equal-power crossfade, so it repeats without a bump. |
| **Verifies the result** | Duration, loudness, true peak, and level spot-checks at five points so a dropout can't hide in hour two. |

Two hours of finished video takes about 8 minutes, nearly all of it the audio pass.

---

## Common recipes

```bash
# The Franky video, reproduced exactly
cozyloop build ~/clips/franky --preset rainy-shop -d 2h -o franky_2h.mp4

# Lofi study video with your own music under rain and vinyl crackle
cozyloop build ~/clips/cafe --preset lofi-rain -d 3h \
  --music ~/Music/my_beat.mp3 --music-level 0.6 -o lofi_3h.mp4

# A whole folder of tracks, crossfaded into one long playlist before looping
cozyloop build ~/clips/cafe --preset lofi-rain -d 3h \
  --music ~/Music/lofi_folder -o lofi_3h.mp4

# Fireplace, 8 hours, slower and gentler transitions
cozyloop build ~/clips/cabin --preset fireplace-cabin -d 8h --fade 2.5 -o fire_8h.mp4

# Rain only, no foley, nothing to notice at 3am
cozyloop build ~/clips/window --preset rainy-window -d 2h -o rain_2h.mp4

# Start from a preset but quiet the clock and add a fire
cozyloop build ~/clips/attic --preset cozy-attic \
  --layer clock:0.04 --layer fire:0.22 -d 2h -o attic_2h.mp4

# Audition a bed before committing to a long render
cozyloop audio --preset thunderstorm -d 90 -o test.m4a

# Check something you already made
cozyloop verify video.mp4
```

---

## Presets

`cozyloop presets` lists them with their layers.

| Preset | For |
|---|---|
| `rainy-shop` | Rain on glass, wall clock, rocking chair |
| `rainy-window` | Pure rain, no foley |
| `thunderstorm` | Heavy rain, wind, distant thunder |
| `lofi-rain` | Rain + vinyl crackle + tape hiss, built to sit under music |
| `lofi-room` | Texture only — vinyl, hiss, room, fan. For music-led videos |
| `fireplace-cabin` | Fire, wind outside, settling timber |
| `snow-cabin` | Winter wind, low fire, deep room |
| `cozy-attic` | Rain on the roof, a clock, an old house moving |
| `study-room` | Quiet room, ticking clock, HVAC |
| `night-forest` | Crickets, soft wind, open air |
| `ocean-night` | Swell and wind on a dark beach |

### Layers

Mix freely with `--layer name[:level]`. Adding a layer already in the preset overrides its level.

`rain` `spray` `drips` `street` `wind` `thunder` `waves` `roomtone` `hum` `fan`
`clock` `creak` `knock` `fire` `crickets` `vinyl` `hiss`

Levels are roughly 0.0–0.5. Typical starting points: beds (`rain`, `fire`, `waves`) around
0.3; room layers around 0.15; foley (`clock`, `creak`) around 0.08. Auto-gain compensates
for the overall level afterwards, so `--layer` changes affect **balance**, not volume.

To build a bed from scratch with no preset, pass `--preset ""` and list layers:

```bash
cozyloop audio --preset "" --layer rain:0.35 --layer clock:0.08 -d 90 -o custom.m4a
```

---

## How many clips do I need?

Cycle length is `n × (clip_length − fade)`. With 10s clips and 1s crossfades:

| Clips | Cycle | Repeats in 2h |
|---|---|---|
| 3 | 27s | 267 |
| 5 | 45s | 160 |
| **8** | **72s** | **100** |
| 12 | 108s | 67 |
| 20 | 180s | 40 |

**8–10 is the sweet spot.** Past that you're paying generation credits for something
nobody awake will notice, and below about 5 the repeat becomes visible in the first few
minutes — which is exactly when a new viewer decides whether to stay.

What matters far more than the count: **clips from the same fixed camera on the same set
cut together almost invisibly.** Two shots of one room beat six shots of six different
rooms. A clip in a noticeably different art style will read as a jump-cut every cycle,
however lovely it is on its own.

## Do the clips need audio?

No — clip audio is discarded entirely (`-an` on the master encode). **Generate with audio
off.** It usually costs extra credits, and per-clip model audio restarts every 10 seconds,
which would pulse audibly across an hour even if it were kept. The bed replaces it.

## Music

`--music` takes files or folders and is repeatable:

```bash
--music track.mp3
--music ~/Music/lofi_folder
--music a.mp3 --music b.mp3 --music ~/more_tracks
```

Multiple tracks are crossfaded end-to-end into one playlist (`sum − 6s × (n−1)`), and only
then wrap-looped. Ten 3-minute tracks give ~29 minutes before anything repeats. For an
8-hour video, more tracks is the only thing that stops the music becoming obvious — the
ambience bed never repeats, but the music does.

## Options worth knowing

| Flag | Default | Notes |
|---|---|---|
| `-d, --duration` | `2h` | `2h`, `90m`, `45m30s`, or raw seconds |
| `--fade` | `1.0` | Crossfade seconds. Longer = dreamier; 2–3s suits slow scenes |
| `--crf` | `20` | 23–24 roughly halves file size with no visible loss on illustrated art |
| `--size` / `--fps` | from clip 1 | e.g. `--size 1920x1080` |
| `--target-lufs` | `-17` | YouTube attenuates loud uploads but won't boost quiet ones |
| `--gain` | auto | Fixed dB; disables auto-gain |
| `--music-level` | `0.55` | Music against the ambience bed |
| `--music-xfade` | `6` | Seam crossfade when looping the music |
| `--fade-in` / `--fade-out` | `10` / `25` | Audio only |

---

## Why the audio is synthesised

Sample packs are the usual route and the usual problem. "Free" collections mix CC0, CC-BY
(attribution required in your video description) and non-commercial (kills monetisation);
licences are frequently mislabelled upstream; and the popular rain and clock recordings are
already in YouTube's Content ID database, which is how ambience channels end up with claims
on a video they believed was clean.

Synthesis sidesteps all of it. The waveform has never existed before, so there is nothing to
claim, nobody to attribute, and no licence to keep track of across a back catalogue.

It also solves the loop problem, which matters more than it sounds. A sampled bed has to be
tiled, and tiled audio has a tell — the ear catches the repeat long before the eye catches
the video loop. Generating one unbroken pass at full length means the bed genuinely never
repeats, and it's the continuous audio that hides the video splices underneath it.

---

## How the seamless loop works

Given clips `A B C` and a 1s crossfade, the tool builds `A→B→C→A` — appending a *second copy*
of A as a final segment — then trims `[1s, end]`.

The result: the last frame lands exactly one frame before the first frame's content, and the
dissolve from C back into A is already baked into the file. Tiling it produces a continuous
dissolve at every junction rather than a hard cut. Master length works out to
`sum(clip lengths) − n × fade`, so three 10s clips with 1s fades give a 27s cycle.

`seam_check` then decodes the actual first and last frames and reports their mean pixel
difference, so you get a number rather than a hope.

---

## Adding your own layer

`lib/ambience.py` is a library of small builder functions. Each returns an ffmpeg filter chain
producing stereo, plus its output label. Add one, register it in `LAYERS`, and it's available
to `--layer` and to any preset.

The building blocks used throughout:

- **Noise beds** — `anoisesrc` (pink/brown/white) band-limited, with a slow `volume` LFO on
  `eval=frame` so it breathes instead of sitting still
- **Stereo width** — two sources with *different seeds* joined to L and R. Duplicating one
  mono source to both channels sounds flat and centred
- **Repeating events** — `aevalsrc` with `exp(-decay*mod(t,period))` gating an oscillator
- **Irregularity** — several incommensurate periods (2.7 / 4.3 / 6.7) summed. The ear cannot
  find the pattern, which is what separates rain from a metronome

## Known limits

- **Aesthetic sounds are approximations.** Rain, fire, wind and clocks synthesise convincingly.
  Human murmur (a café, a diner) does not — use a real bed via `--music` for those.
- **Auto-gain drifts with dynamic music.** A 45s probe can't characterise a whole track; a
  music-led build may land 1–2 LU off target. Check with `cozyloop verify` and set `--gain` if
  it matters.
- **It won't detect burnt-in watermarks.** If a generator baked its UI into the pixels, the
  tool will happily loop it. Eyeball your clips first.
