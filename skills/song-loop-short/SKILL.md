---
name: song-loop-short
description: Build a Song Loop Short — one song played once over vertical (9:16) scenery clips cut to the song's sections, with an ambience bed (e.g. a river), an xil-microclips-style opening card, end card and cover, a separate lyric .srt, upload guides (YouTube Shorts + Substack) and Google Flow prompts written from the lyrics. Use when Tina asks to pair 9:16 clips with one song, make a "sample cozy loop" Short/Reel, "do one song for this loop", or says "Song Loop Short". For hour-long loops use cozy-loop-video; for audio-drama Shorts use xil-microclips.
---

# Song Loop Short

A blend of three things Tina already had: `cozyloop` (clips + ambience), the xil-microclips card
look (cream panel, Playfair title, Quicksand body), and the Scenery_Woonsocket `PROMPTS.md` style of
copy-paste Google Flow prompts. The tool is `cozyloop short <spec.json>` in
`~/cozy-loop-kit` (`src/cozyloop/short.py`; example spec `examples/river-knows.short.json`).
First one: "The River Knows", 2026-09-30, in `~/Ambient_Videos/Cozy_Loop_Builds/woonsocket_river_knows_short/`.

## 1. Ask first (multiple choice, one round at a time)

Tina likes multiple-choice questions until everything is settled. Recommend an option and put it first.

1. **Song**: list the full-length tracks in the folder with durations. Flag anything over ~2:55,
   because with a 5 s end card it passes the 3-minute Shorts limit and posts as a regular video.
2. **Length**: one play of the song (default), or longer with repeats. For longer, use cozy-loop-video.
3. **Clips**: all clean ones, a theme (e.g. water only), or pick by number from a contact sheet.
4. **Pacing**: about 8–9 s per clip. 40+ clips in a 2:30 song is too fast; recommend the best ~16–20.
5. **Ambience bed**: real SFX, never synthesized. For Woonsocket, use the show's steady river:
   `~/NAS/xil-projects/SFX/thewoonsocketwonders/AMBIENCE-_Gentle_River_Flowing.mp3` (10 s, looped). It's
   the same bed as the other explainers. Tina said a blend of several river files was "too loud" and
   "too erratic" (2026-09-30). Keep the river faint. Reject files with music baked in.
6. **Style outliers** (a brighter or summery "memory" set): ask. They can be a deliberate moment,
   e.g. golden memory on the last chorus.
7. **Card text**: opening card (kicker / title / credit lines), end card (what it points to), cover.
8. **Upload guides**: which platforms. **Flow prompts**: one still + one video per lyric section (default).
9. **Her note** ("why I make these") in her own words, verbatim. Don't reuse an old one.
10. **Process reel**: ask. Skip it when the art isn't her own. River Knows: she said the scenery was
    inspired by real photos, not her original work.
11. **AI disclosure**: the description line plus YouTube's altered-content toggle (brand-core default).

**Captions: never burn them in** (Tina, 2026-09-30). Ship a lyric `.srt` for YouTube CC.

## 2. Vet the clips

- `cozyloop short spec.json --sheet` writes 5 frames per timeline clip (0.2 s, 1.5 s, middle, 75%, end).
- Look for:
  - baked-in text (place and date titles, signs with the wrong year)
  - watermarks
  - rounded "card" borders and signatures
  - paint blobs
  - scene glitches (e.g. a sky pasted over a ceiling)
- **Generators fade titles out in the first ~2.5 s.** A mid-clip frame looks clean. Keep the clip
  and give it an in-point (`[start, "clip.mp4", 2.6]`), or crop if the mark is persistent.
- The scenery library is 720x1280 (one 1080x1920). The tool upscales to 1080x1920 with lanczos.

## 3. Find the song's sections

```bash
ffmpeg -i song.mp3 -ar 16000 -ac 1 /tmp/s.wav
whisper-cli -m ~/.cache/whisper-cpp/ggml-base.en.bin -f /tmp/s.wav -ml 44 -sow
```

Use the times for the sections (intro, verses, choruses, outro) and to match scenery to lyrics
(cobblestones on "cobblestones gleam", lamps on "lanterns"). **Whisper mishears sung lyrics**
("Whose socket" = Woonsocket). Ask Tina for the real lyrics, or flag the uncertain lines in UPLOAD.md.

## 4. Spec, cards, render

1. Copy `~/cozy-loop-kit/examples/river-knows.short.json` into the build folder. Set song, clips_root, timeline, bed, intro, end_card and cover.
2. **Timeline rule:** each clip plays from its start to the next start. It needs `in-point + slot + xfade (1 s)` of footage. `cozyloop short` checks this and names the clip that's too short.
3. Run `cozyloop short spec.json --cards`. That writes the `.cover.jpg`, `.end_card.png` and `.intro_preview.jpg`. **Look at them.**
4. Run `cozyloop short spec.json`. That does the full render and prints length, LUFS and true peak. Targets: −14 LUFS, −1 dBTP, 1080x1920, 30 fps.
5. Extract frames at every in-point clip and at the end card, and read them before calling it done.

Mix defaults:
- `bed_level` 1.4: each bed file is levelled to −30 LUFS first, which puts the river ~13 dB under the song. It's still audible under the end card at about −24 LUFS.
- 0.3 was inaudible (−25 dB under the song).

## 5. Deliverables (in the build folder)

| File | Notes |
|---|---|
| `<slug>.mp4`, `.cover.jpg`, `.end_card.png` | from `cozyloop short` |
| `<slug>.en.srt` | lyric captions: ≤32 characters per line, 2 lines, ≥1 s each, `[sound cues]` at start and end. Not burned in. |
| `UPLOAD.md` | Covers: files table; lyric lines to check; YouTube Shorts title (≤100 characters, counted), description with her note verbatim, timestamps on the song sections and an AI disclosure; pinned comment; settings (thumbnail, captions upload, audience "Not made for kids", altered content Yes, Related video, playlist); Substack post + Note + alt text. No emoji. |
| `FLOW_PROMPTS.md` | Starts with the "Flow project instructions (paste once)" block. Then one still + one Frames-to-Video prompt per lyric section, each with the full style block. The song's characters appear only as traces: no people or animals. Note "Have: …" where the library already covers a scene. |

Put the build in `~/Ambient_Videos/Cozy_Loop_Builds/<slug>/`, and use a unique work folder (memory: feedback_cozyloop_work_dir_collision).

## Brand notes

- Woonsocket look: `DEFAULT_LOOK` in short.py (the microclips series profile).
- For another brand, pass `look` in the spec: fonts and colours from its brand-system folder.
- Load `brand-core` first. Write "Wisdom and Wires Studio", never "&". Substack: wisdomandwiresstudio.substack.com.
