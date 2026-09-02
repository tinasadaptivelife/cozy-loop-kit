# <project> — storyboard

Copy this file into the project, rename to `STORYBOARD.md`, and fill in what you know.
Blank cells fall back to the defaults noted under the table. Leave a cell as
`pick: <description>` to have the clip chosen from the footage inventory.

---

## Global

| Setting | Value |
|---|---|
| Aspect / res | 16:9 · 4K (3840×2160) · 24 fps |
| Target length | ~12 min |
| Mood / pace | slow, nostalgic, unhurried; landscapes breathe, interiors cut quicker |
| Music (in order) | 1) ____  2) ____  3) ____  4) ____  5) ____ |
| Default audio | music only |
| Card style | Canva PNGs — <link or attach> |
| Transition | crossfade 0.7 s default; dip-to-black at section breaks |

---

## Beats

| # | Section | Clip / what we see | Hold | Audio | Text | In | Intent |
|---|---------|--------------------|------|-------|------|----|--------|
| 1 | — | CARD `open.png` | 4s | music | — | — | quiet start |
| 2 | Morning | `IMG_9967` | normal | music | overlay "6:14 a.m." lower-left @1–4s | fade 1.0s | hello, still sleepy |
| 3 | Morning | pick: the house waking up | breathe | music | — | fade 0.7s | light coming in |
| 4 | The lake | `IMG_0428` | breathe | native up | — | dip-black | still grey water |
| 5 | — | CARD `t1.png` | 5s | music | (or type the line; it'll be typeset) | fade | first reflection |
| 6 | … | … | … | … | … | … | … |

---

## Column reference

- **Section** — free label; used only to place dip-to-black breaks and group the arc.
- **Clip / what we see** — an `IMG_xxxx` id, or `pick: <description>` to choose from the
  inventory, or `CARD <file.png>` for a full-screen card.
- **Hold** — `quick` (~3 s) · `normal` (~5–6 s) · `breathe` (~9–12 s), or an explicit
  number of seconds. Blank = `normal`.
- **Audio** — blank = music only. `native up` = clip's own sound forward, music ducked.
  `native bed` = clip sound low under music. `ambient: <file>` = separate recording under
  this beat.
- **Text** — blank = none. `CARD <file.png>` · `overlay "<text>" <position> @<in>–<out>s`
  (position: lower-left / lower-center / center / upper-right …) · or just type the line
  and it'll be set in a system serif.
- **In** — transition *into* this beat. Blank = `crossfade 0.7s`. Also `fade <sec>`,
  `cut`, `dip-black`.
- **Intent** — one line on the feeling. Guides clip choice and hold length where the
  beat is left loose.

---

## Open questions

<!-- Questions raised during drafting land here. Answer inline. -->
