# Video-diary workflow

Real phone footage + music + place cards / "thought of the day" messages, cut into a
short film of a day. A separate track from the cozy-loop sleep videos — different pacing,
different tools, its own process.

---

## How to start one

Drop the footage and music somewhere and say, at minimum:

> "New video diary — clips are in `<folder>`."

That's enough to begin. Everything below is optional colour you can add now or answer
when asked.

### Kickoff questions (asked every project)

Answer as many or as few as you want; anything left open gets drafted for you to react to.

1. **Theme** — what this episode is about, or "just the day."
2. **Feel** — pace and emotional register. Reference videos welcome.
3. **Length** — target runtime. You'll be told whether the footage supports it.
4. **Messages** — do you have the card / overlay text now, will you write it after seeing
   a proof, or should candidate lines be drafted for you?
5. **Music** — specific tracks, or a mood to pull from the library.
6. **Native sound** — any clips that must keep their own audio; is there a separate
   ambient recording to lay under the video.
7. **Hands-on level** — are you laying out the beats yourself, or should the storyboard
   be drafted for you to react to?

### Adaptive rule

Whatever you direct is executed exactly, with any conflict flagged. Whatever you leave
open or mark "you decide" is drafted, and you react to it in the storyboard doc — not in
a render.

---

## Pipeline

| Stage | What happens | You do |
|---|---|---|
| **1. Footage inventory** | Contact sheet + a numbered line per clip: description, length, whether the audio is usable, flags (near-dupes, resolution outliers, shake, watermarks). | Skim it. |
| **2. Storyboard** | `STORYBOARD.md` is filled in — by you, or drafted from the inventory to whatever degree you left open. Open questions sit inline in the doc. | Mark it up. Iterate on the doc. |
| **3. 1080p proof** | Fast render of the locked storyboard. Placeholder cards if the real ones aren't ready. | Watch. Send notes + final card/overlay art. |
| **4. 4K final** | Native-resolution render with crossfades and your Canva cards composited in. | — |

Steps 2–3 loop cheaply on text. Only step 4 is slow.

---

## Baked-in defaults

Override any of these in the storyboard's **Global** block or per beat.

- **Audio:** music only. Native clip sound is opt-in per beat and is ducked ~12–18 dB
  under the music with ~0.5 s fades. Supply a clean separate ambient recording if you
  want room tone throughout.
- **Transitions:** ~0.7 s crossfade between clips, 1–1.5 s on landscapes. Dip-to-black
  only at section breaks and around cards.
- **Cards & text overlays:** authored in Canva as **1920×1080 PNG** — transparent
  background for overlays. They're composited and upscaled with the 4K footage. The
  render machine has no font renderer, so any text that isn't supplied as art gets
  typeset in a plain system serif.
- **Format:** 16:9, native 4K (3840×2160), 24 fps.

---

## How many clips for a given length

`finished minutes ≈ (clips × avg hold + cards × card hold) ÷ 60`

Phone clips of everyday moments hold ~4–8 s before they feel static. Landscapes can go
10–15 s. So:

| Target | Clips at ~8 s avg | Clips at ~13 s avg |
|---|---|---|
| 10 min | ~55 | ~35 |
| 16 min | ~85 | ~55 |
| 20 min | ~105 | ~70 |

Plus 6–12 cards. If one day doesn't yield that, make the episode a multi-day compilation.

**Music:** 5–6 tracks per 15–20 min. Skip the ~30 s preview snippets in the library.
