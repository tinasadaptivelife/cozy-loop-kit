"""
Procedural ambience layer library for cozy-loop videos.

Every layer is synthesised from noise/oscillator sources in ffmpeg. Nothing is
sampled, so there is nothing to license, nothing to attribute, and nothing for
Content ID to match against. A bed is generated in a single pass at full length,
so it never repeats no matter how long the video runs.

Each builder returns (filter_chain_string, output_label) producing STEREO audio.
"""

PI = "PI"


class SeedPool:
    """Unique noise seeds so no two layers share a waveform."""

    def __init__(self, start=101):
        self.n = start

    def next(self):
        self.n += 97
        return self.n


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _noise(color, seed, dur, amp=0.9):
    return f"anoisesrc=c={color}:r=48000:a={amp}:d={dur}:s={seed}"


def _mono2st(gain_l=1.0, gain_r=1.0):
    return f"pan=stereo|c0={gain_l}*c0|c1={gain_r}*c0"


def _decay_pulses(periods, freqs, decay, weights=None):
    """Sum of damped sinusoids on the given periods. Incommensurate periods
    read as irregular; a single period reads as a metronome."""
    weights = weights or [1.0] * len(periods)
    parts = []
    for p, f, w in zip(periods, freqs, weights):
        parts.append(f"{w}*exp(-{decay}*mod(t,{p}))*sin(2*PI*{f}*t)")
    return "+".join(parts)


# --------------------------------------------------------------------------
# WEATHER
# --------------------------------------------------------------------------

def rain(sp, dur, label, level=0.34, lo=280, hi=7800, gust=97, depth=0.40):
    """Main rain body — pink noise, stereo-decorrelated with separate seeds per
    channel so it opens up in headphones.

    Three gust LFOs on incommensurate periods, the longest around 97s. Weather
    moves on a scale of minutes; anything faster reads as tremolo rather than as
    a squall passing over. `depth` is the total swing either side of centre —
    0.40 gives roughly 10 dB between the lulls and the downpours.
    """
    a, b = sp.next(), sp.next()
    band = f"highpass=f={lo}:poles=2,lowpass=f={hi}:poles=2"
    d1, d2, d3 = depth * 0.55, depth * 0.30, depth * 0.15
    lfo = (f"({1-depth}+{d1}*sin(2*PI*t/{gust})"
           f"+{d2}*sin(2*PI*t/{gust*0.38:.1f}+1)"
           f"+{d3}*sin(2*PI*t/{gust*0.135:.1f}+2))")
    return (
        f"{_noise('pink', a, dur)},{band}[{label}_l];"
        f"{_noise('pink', b, dur)},{band}[{label}_r];"
        f"[{label}_l][{label}_r]join=inputs=2:channel_layout=stereo,"
        f"volume='{level}*{lfo}':eval=frame[{label}]"
    ), label


def spray(sp, dur, label, level=0.26, lo=3200, hi=9500, gust=71):
    """Fine high-band spray — the hiss of drops bursting on glass."""
    a, b = sp.next(), sp.next()
    band = f"highpass=f={lo}:poles=2,lowpass=f={hi}:poles=2"
    return (
        f"{_noise('pink', a, dur)},{band}[{label}_l];"
        f"{_noise('pink', b, dur)},{band}[{label}_r];"
        f"[{label}_l][{label}_r]join=inputs=2:channel_layout=stereo,"
        f"volume='{level}*(0.78+0.22*sin(2*PI*t/{gust}+2))':eval=frame"
        f"[{label}]"
    ), label


def drips(sp, dur, label, level=0.055):
    """Drips off the eaves. Three incommensurate periods so the ear never
    locks onto a pattern."""
    expr = _decay_pulses([2.7, 4.3, 6.7], [1400, 1750, 1150], 90, [1.0, 0.85, 0.7])
    return (
        f"aevalsrc=exprs='{expr}':s=48000:d={dur},"
        f"highpass=f=600:poles=2,aecho=0.9:0.3:23|41:0.20|0.12,"
        f"volume={level},{_mono2st(0.75, 1.0)}[{label}]"
    ), label


def street(sp, dur, label, level=0.42, cutoff=320, gust=83, depth=0.28):
    """Rain hitting pavement outside — the low rumble under everything. Swells
    on a longer, offset cycle from the main rain so the two drift against each
    other instead of pumping in lockstep."""
    a = sp.next()
    return (
        f"{_noise('brown', a, dur)},lowpass=f={cutoff}:poles=2,"
        f"volume='{level}*({1-depth}+{depth*0.7:.3f}*sin(2*PI*t/{gust}+1)"
        f"+{depth*0.3:.3f}*sin(2*PI*t/{gust*0.44:.1f}+2))':eval=frame,"
        f"{_mono2st()}[{label}]"
    ), label


def wind(sp, dur, label, level=0.30, cutoff=700, gust=19, depth=0.45):
    """Gusting wind. Deeper LFO than rain, so it swells rather than breathes."""
    a, b = sp.next(), sp.next()
    band = f"lowpass=f={cutoff}:poles=2,highpass=f=90:poles=1"
    return (
        f"{_noise('brown', a, dur)},{band}[{label}_l];"
        f"{_noise('brown', b, dur)},{band}[{label}_r];"
        f"[{label}_l][{label}_r]join=inputs=2:channel_layout=stereo,"
        f"volume='{level}*({1-depth}+{depth}*(0.5+0.5*sin(2*PI*t/{gust})))':eval=frame"
        f"[{label}]"
    ), label


def thunder(sp, dur, label, level=1.2, period=58, crack=0.30, rumble=1.7,
            triggers=None, cycle=None, delay=3.0):
    """Distant thunder: a short crack, then a long rolling rumble.

    Two earlier versions got this wrong in opposite directions. One band
    lowpassed at 180 Hz was pure sub-bass sitting exactly where rain and waves
    already are — masked, 3.7 dB over the bed, inaudible. Adding a fast
    280-2400 Hz band made it audible but turned it into a bang, because the
    rumble under it decayed at 4.8 dB/s: gone in three seconds.

    Real distant thunder cracks once and then rolls for ten seconds or more,
    wandering in level as the wavefront bounces. So the low band now runs to
    420 Hz (above the worst of the wave masking), decays at ~2.4 dB/s, and is
    modulated by a slow wobble so the tail moves instead of fading flat.
    """
    a, b = sp.next(), sp.next()
    if triggers and cycle:
        # Lock the strikes to the picture. Lightning arrives instantly and the
        # sound lags by distance, so each flash gets its thunder `delay`
        # seconds later, repeating on the visual loop. Without this, footage
        # that flashes every few seconds plays over near-silence and the gap
        # is more noticeable than the thunder ever was.
        slow_terms, fast_terms = [], []
        for i, o in enumerate(triggers):
            w = (1.0, 0.5, 0.8, 0.4)[i % 4]
            x = f"mod(t+{(cycle - (o + delay) % cycle) % cycle:.2f},{cycle:.2f})"
            wob = f"(0.62+0.38*sin(2*PI*{x}*0.7)*exp(-0.15*{x}))"
            slow_terms.append(
                f"{w}*({wob})*exp(-0.28*{x})*(1-exp(-2.2*{x}))")
            fast_terms.append(
                f"{w}*exp(-2.4*{x})*(1-exp(-30*{x}))")
        slow, fast = "+".join(slow_terms), "+".join(fast_terms)
    else:
        p2, off = period * 1.7, period * 0.61
        # the roll: slow decay, wobbling, so the tail keeps moving
        roll = (f"(0.62+0.38*sin(2*PI*mod(t,{period})*0.7)"
                f"*exp(-0.15*mod(t,{period})))")
        slow = (f"({roll})*(exp(-0.28*mod(t,{period}))"
                f"*(1-exp(-2.2*mod(t,{period})))"
                f"+0.7*exp(-0.26*mod(t+{off:.2f},{p2:.2f}))"
                f"*(1-exp(-2.0*mod(t+{off:.2f},{p2:.2f}))))")
        # the crack: fast in, fast out, and deliberately quieter than the roll
        fast = (f"exp(-2.4*mod(t,{period}))*(1-exp(-30*mod(t,{period})))"
                f"+0.7*exp(-2.2*mod(t+{off:.2f},{p2:.2f}))"
                f"*(1-exp(-28*mod(t+{off:.2f},{p2:.2f})))")
    return (
        f"{_noise('brown', a, dur)},lowpass=f=420:poles=2,highpass=f=35:poles=1,"
        f"volume='{slow}':eval=frame,volume={rumble}[{label}_lo];"
        f"{_noise('brown', b, dur)},highpass=f=300:poles=2,"
        f"lowpass=f=2200:poles=2,"
        f"volume='{fast}':eval=frame,volume={crack}[{label}_hi];"
        f"[{label}_lo][{label}_hi]amix=inputs=2:normalize=0,"
        f"volume={level},{_mono2st()}[{label}]"
    ), label


def waves(sp, dur, label, level=0.40, swell=11.5, lo=25, hi=3200):
    """Ocean swell — noise shaped by a slow asymmetric envelope."""
    a, b = sp.next(), sp.next()
    band = f"lowpass=f={hi}:poles=2,highpass=f={lo}:poles=2"
    env = f"(0.30+0.70*pow(0.5+0.5*sin(2*PI*t/{swell}),2.2))"
    return (
        f"{_noise('pink', a, dur)},{band}[{label}_l];"
        f"{_noise('pink', b, dur)},{band}[{label}_r];"
        f"[{label}_l][{label}_r]join=inputs=2:channel_layout=stereo,"
        f"volume='{level}*{env}':eval=frame[{label}]"
    ), label


def current(sp, dur, label, level=0.34, cutoff=520, lo=40, swell=29, depth=0.42):
    """Water moving past you, heard from under the surface.

    Underwater is a lowpass: the high band doesn't survive the trip, so this is
    brown noise rolled off hard and swelled on a slow, drifting cycle. Separate
    seeds per channel keep it wide, but the two are pulled toward each other by
    the shared LFO the way a body of water moves as one thing.

    Water also doesn't carry much *sub* — a hydrophone recording sits in the
    mids, not the bottom octave — so `lo` exists to pull the floor up out of
    rumble territory when the footage is a body moving, not a deep swell.
    """
    a, b = sp.next(), sp.next()
    band = f"lowpass=f={cutoff}:poles=2,highpass=f={lo}:poles=2"
    lfo = (f"({1-depth}+{depth*0.6:.3f}*sin(2*PI*t/{swell})"
           f"+{depth*0.25:.3f}*sin(2*PI*t/{swell*0.41:.1f}+1)"
           f"+{depth*0.15:.3f}*sin(2*PI*t/{swell*0.17:.1f}+2))")
    return (
        f"{_noise('brown', a, dur)},{band}[{label}_l];"
        f"{_noise('brown', b, dur)},{band}[{label}_r];"
        f"[{label}_l][{label}_r]join=inputs=2:channel_layout=stereo,"
        f"volume='{level}*{lfo}':eval=frame[{label}]"
    ), label


def swish(sp, dur, label, level=0.12, lo=380, hi=1900, period=6.7):
    """The mid-band wash of a body moving through water — a swimmer's stroke.
    Narrower and faster than `current`, so it reads as motion against the
    water rather than as the water itself."""
    a, b = sp.next(), sp.next()
    band = f"highpass=f={lo}:poles=2,lowpass=f={hi}:poles=2"
    h = period / 2
    env = (f"(0.18+0.82*(exp(-2.6*mod(t,{period}))*(1-exp(-9*mod(t,{period})))"
           f"+0.7*exp(-3.1*mod(t+{h},{period}))*(1-exp(-11*mod(t+{h},{period})))))")
    return (
        f"{_noise('pink', a, dur)},{band}[{label}_l];"
        f"{_noise('pink', b, dur)},{band}[{label}_r];"
        f"[{label}_l][{label}_r]join=inputs=2:channel_layout=stereo,"
        f"volume='{level}*{env}':eval=frame[{label}]"
    ), label


def bubbles(sp, dur, label, level=0.14, fizz=0.35):
    """Bubbles rising past the ear.

    A bubble is a resonating cavity, and as it rises the pressure drops, the
    cavity grows — but the oscillation it radiates *sweeps upward* as the
    bubble pinches off and shrinks. That rising chirp is the whole character;
    a flat damped sine is a marimba, not a bloop. Frequency is the derivative
    of phase, so an upward glide needs a positive squared phase term.

    Six incommensurate periods so the stream never falls into a pattern, plus a
    fine fizz of small bubbles too little to hear individually. `fizz` is the
    balance between the two.
    """
    a = sp.next()
    specs = [  # period, start freq, glide, decay, weight
        (1.13, 560,  820, 19, 1.00),
        (1.79, 740, 1080, 23, 0.72),
        (2.71, 430,  600, 15, 0.88),
        (4.31, 930, 1400, 27, 0.45),
        (6.53, 640,  900, 21, 0.66),
        (9.7,  360,  480, 12, 0.60),
    ]
    parts = []
    for p, f0, k, d, w in specs:
        u = f"mod(t,{p})"
        parts.append(f"{w}*exp(-{d}*{u})*sin(2*PI*({f0}*{u}+{k}*{u}*{u}))")
    blo = "+".join(parts)
    return (
        f"aevalsrc=exprs='{blo}':s=48000:d={dur},"
        f"bandpass=f=650:width_type=h:w=1100,"
        f"aecho=0.9:0.3:27|43:0.18|0.11,"
        f"volume={level * (1 - fizz):.4f},{_mono2st(0.88, 1.0)}[{label}_b];"
        f"{_noise('white', a, dur)},bandpass=f=4200:width_type=h:w=3000,"
        f"volume='0.35+0.65*pow(0.5+0.5*sin(2*PI*t/13.7),2)':eval=frame,"
        f"volume={level * fizz:.4f},{_mono2st(1.0, 0.85)}[{label}_f];"
        f"[{label}_b][{label}_f]amix=inputs=2:duration=first:normalize=0[{label}]"
    ), label


# --------------------------------------------------------------------------
# ROOM
# --------------------------------------------------------------------------

def roomtone(sp, dur, label, level=0.16, cutoff=170):
    """The sound of a room being a room. Almost inaudible alone, badly missed
    when absent — it's what stops a bed sounding synthetic."""
    a = sp.next()
    return (
        f"{_noise('brown', a, dur)},lowpass=f={cutoff}:poles=2,"
        f"volume={level},{_mono2st()}[{label}]"
    ), label


def hum(sp, dur, label, level=0.011, freq=112):
    """Fridge / display case / transformer hum."""
    return (
        f"sine=frequency={freq}:sample_rate=48000:duration={dur},"
        f"volume={level},{_mono2st()}[{label}]"
    ), label


def fan(sp, dur, label, level=0.22):
    """HVAC or a desk fan — broadband push with a faint blade tone."""
    a = sp.next()
    return (
        f"{_noise('brown', a, dur)},lowpass=f=520:poles=2,highpass=f=60:poles=1,"
        f"volume={level},{_mono2st()}[{label}]"
    ), label


# --------------------------------------------------------------------------
# ASMR / FOLEY
# --------------------------------------------------------------------------

def clock(sp, dur, label, level=0.085, tick=1.0):
    """Wall clock. Tick and tock differ in timbre on a 2-tick cycle, each strike
    a damped two-tone plus a broadband snap, through a small-room echo."""
    p = tick * 2
    expr = (
        f"exp(-75*mod(t,{p}))*(0.55*sin(2*PI*2550*t)+0.35*sin(2*PI*1180*t))"
        f"+0.85*exp(-75*mod(t+{tick},{p}))*(0.55*sin(2*PI*2150*t)+0.35*sin(2*PI*990*t))"
        f"+0.45*exp(-320*mod(t,{p}))*(random(0)-0.5)"
        f"+0.38*exp(-320*mod(t+{tick},{p}))*(random(1)-0.5)"
    )
    return (
        f"aevalsrc=exprs='{expr}':s=48000:d={dur},"
        f"highpass=f=500:poles=2,lowpass=f=7000:poles=2,"
        f"aecho=0.9:0.35:17|29:0.22|0.13,"
        f"volume={level},{_mono2st(0.92, 0.74)}[{label}]"
    ), label


def _creak_voice(u, f0, glide, rough_f, rough_g, amp=1.0):
    """One stick-slip creak.

    A creak is not a pitch, it's a *friction* event: the wood grips, slips,
    grips again, hundreds of times a second. Two things follow, and both are
    what separate a creak from a musical note —

    1. It GLIDES. The contact stiffens as the joint loads, so the pitch slides.
       Frequency is the derivative of phase, so a linear glide needs a squared
       phase term: sin(2*PI*(f0*u + k*u^2)) sweeps from f0 to f0 + 2*k*u.
    2. It's ROUGH. The stick-slip cycle amplitude-modulates the tone at a few
       tens of Hz, which the ear reads as creaky rather than as a tone. That
       modulation glides too.

    Clean harmonic sines with no glide and no roughness sound like a piano key,
    because that is essentially what a piano key is.
    """
    ph = lambda f, k: f"sin(2*PI*({f}*{u}+{k}*{u}*{u}))"
    rough = f"({1 - rough_g}+{rough_g}*sin(2*PI*({rough_f}*{u}+{rough_f * 0.7:.1f}*{u}*{u})))"
    # inharmonic partials — a resonating wooden joint is not a harmonic series
    body = (f"({ph(f0, glide)}"
            f"+0.62*{ph(round(f0 * 1.63), round(glide * 1.63))}"
            f"+0.34*{ph(round(f0 * 2.41), round(glide * 2.41))})")
    return f"{amp}*{rough}*{body}"


def creak(sp, dur, label, level=0.16, period=3.4, tonal=0.62):
    """Wood friction — a rocking chair, a floorboard, a hull. Twice per cycle
    (forward and back), each a stick-slip event that glides and buzzes.

    Broadband rain masks broadband foley almost perfectly however loud you make
    it — noise hides inside noise — so this can't be pure filtered noise. But
    pure tone reads as an instrument. The answer is a rough, gliding, inharmonic
    voice plus a friction-noise bed: narrow enough to cut through the rain,
    dirty enough to sound like wood. `tonal` is the tone/friction balance.
    """
    a = sp.next()
    h = period / 2
    ua, ub = f"mod(t,{period})", f"mod(t+{h},{period})"
    env_a = f"exp(-6.5*{ua})*(1-exp(-28*{ua}))"
    env_b = f"exp(-6.5*{ub})*(1-exp(-28*{ub}))"
    # forward creak pitches down as the rocker settles; the back creak is
    # higher and shorter, as the joint unloads
    voice = (f"{env_a}*{_creak_voice(ua, 505, -210, 41, 0.45)}"
             f"+{env_b}*{_creak_voice(ub, 583, -260, 47, 0.5, amp=0.8)}")
    return (
        f"aevalsrc=exprs='{voice}':s=48000:d={dur},"
        f"highpass=f=180:poles=1,lowpass=f=3000:poles=2,"
        f"aecho=0.9:0.3:19|31:0.18|0.11,"
        f"volume={level * tonal:.4f},{_mono2st(0.70, 0.95)}[{label}_t];"
        f"{_noise('white', a, dur)},bandpass=f=620:width_type=h:w=900,"
        f"volume='{env_a}+0.8*{env_b}':eval=frame,"
        f"volume={level * (1 - tonal):.4f},{_mono2st(0.75, 0.95)}[{label}_n];"
        f"[{label}_t][{label}_n]amix=inputs=2:duration=first:normalize=0[{label}]"
    ), label


def knock(sp, dur, label, level=0.10, period=3.4):
    """The weight shift under a creak — low thump on the same cycle."""
    h = period / 2
    expr = (f"exp(-22*mod(t,{period}))*sin(2*PI*95*t)"
            f"+0.8*exp(-22*mod(t+{h},{period}))*sin(2*PI*78*t)")
    return (
        f"aevalsrc=exprs='{expr}':s=48000:d={dur},"
        f"lowpass=f=300:poles=2,volume={level},{_mono2st()}[{label}]"
    ), label


def fire(sp, dur, label, level=0.30):
    """Fireplace — a filtered roar plus pops on incommensurate periods."""
    a = sp.next()
    pops = _decay_pulses(
        [1.7, 2.9, 4.7, 7.3, 11.1],
        [900, 1400, 620, 1750, 480],
        140,
        [1.0, 0.8, 0.9, 0.6, 0.7],
    )
    return (
        f"{_noise('brown', a, dur)},lowpass=f=900:poles=2,"
        f"volume='{level}*(0.7+0.3*sin(2*PI*t/8.3)+0.15*sin(2*PI*t/3.1))':eval=frame,"
        f"{_mono2st()}[{label}_bed];"
        f"aevalsrc=exprs='{pops}':s=48000:d={dur},"
        f"highpass=f=400:poles=2,volume={level*0.45:.4f},{_mono2st(0.9, 0.8)}[{label}_pop];"
        f"[{label}_bed][{label}_pop]amix=inputs=2:duration=first:normalize=0[{label}]"
    ), label


def crickets(sp, dur, label, level=0.05):
    """Night insects — narrow high chirps, several offset periods."""
    expr = _decay_pulses([0.31, 0.47, 0.73], [4300, 4750, 3900], 55, [1.0, 0.7, 0.5])
    return (
        f"aevalsrc=exprs='{expr}':s=48000:d={dur},"
        f"bandpass=f=4400:width_type=h:w=1400,"
        f"volume='{level}*(0.6+0.4*sin(2*PI*t/17))':eval=frame,"
        f"{_mono2st(0.8, 1.0)}[{label}]"
    ), label


# --------------------------------------------------------------------------
# LOFI TEXTURE
# --------------------------------------------------------------------------

def vinyl(sp, dur, label, level=0.09):
    """Record surface noise — sparse crackle plus a rotation-rate thump."""
    a = sp.next()
    crackle = _decay_pulses(
        [0.37, 0.53, 0.91, 1.33, 2.11],
        [3200, 5100, 2400, 6300, 1900],
        420,
        [1.0, 0.8, 0.9, 0.6, 0.7],
    )
    return (
        f"aevalsrc=exprs='{crackle}':s=48000:d={dur},"
        f"highpass=f=1200:poles=2,volume={level},{_mono2st(0.95, 0.85)}[{label}_c];"
        f"{_noise('pink', a, dur)},bandpass=f=60:width_type=h:w=40,"
        f"volume='0.05*(1-exp(-3*mod(t,1.8)))':eval=frame,{_mono2st()}[{label}_r];"
        f"[{label}_c][{label}_r]amix=inputs=2:duration=first:normalize=0[{label}]"
    ), label


def hiss(sp, dur, label, level=0.035):
    """Tape hiss. Glues a mix together at levels you can barely hear."""
    a, b = sp.next(), sp.next()
    return (
        f"{_noise('pink', a, dur)},highpass=f=2200:poles=2[{label}_l];"
        f"{_noise('pink', b, dur)},highpass=f=2200:poles=2[{label}_r];"
        f"[{label}_l][{label}_r]join=inputs=2:channel_layout=stereo,"
        f"volume={level}[{label}]"
    ), label


# --------------------------------------------------------------------------
LAYERS = {
    "rain": rain, "spray": spray, "drips": drips, "street": street,
    "wind": wind, "thunder": thunder, "waves": waves,
    "current": current, "swish": swish, "bubbles": bubbles,
    "roomtone": roomtone, "hum": hum, "fan": fan,
    "clock": clock, "creak": creak, "knock": knock,
    "fire": fire, "crickets": crickets,
    "vinyl": vinyl, "hiss": hiss,
}

# Presets are just ordered layer lists with overrides.
PRESETS = {
    "rainy-shop": {
        "desc": "Rain on shop glass, rumble, and a wall clock. The Franky bed.",
        "layers": [("rain", {}), ("spray", {}), ("drips", {"level": 0.16}),
                   ("street", {}), ("roomtone", {}), ("hum", {}),
                   ("clock", {"level": 0.34})],
    },
    "rainy-window": {
        "desc": "Pure rain on glass. No foley, nothing to notice.",
        "layers": [("rain", {"level": 0.38}), ("spray", {}), ("drips", {}),
                   ("street", {}), ("roomtone", {})],
    },
    "thunderstorm": {
        "desc": "Heavy rain, wind, distant thunder.",
        "layers": [("rain", {"level": 0.42, "hi": 8600}), ("spray", {"level": 0.30}),
                   ("street", {"level": 0.38}), ("wind", {"level": 0.26}),
                   ("thunder", {}), ("roomtone", {})],
    },
    "lofi-rain": {
        "desc": "Rain + vinyl crackle + tape hiss. Built to sit under music.",
        "layers": [("rain", {"level": 0.26}), ("spray", {"level": 0.18}),
                   ("street", {"level": 0.22}), ("roomtone", {}),
                   ("vinyl", {}), ("hiss", {})],
    },
    "lofi-room": {
        "desc": "Just texture — vinyl, hiss, room, fan. For music-led videos.",
        "layers": [("roomtone", {"level": 0.20}), ("fan", {"level": 0.16}),
                   ("vinyl", {}), ("hiss", {}), ("hum", {})],
    },
    "fireplace-cabin": {
        "desc": "Fire, wind outside, settling timber.",
        "layers": [("fire", {}), ("wind", {"level": 0.20}), ("roomtone", {}),
                   ("creak", {"level": 0.20, "period": 9.3})],
    },
    "snow-cabin": {
        "desc": "Winter wind, low fire, deep room.",
        "layers": [("wind", {"level": 0.34, "cutoff": 900, "gust": 23}),
                   ("fire", {"level": 0.18}), ("roomtone", {"level": 0.20}),
                   ("creak", {"level": 0.18, "period": 11.7})],
    },
    "cozy-attic": {
        "desc": "Rain on the roof and a clock.",
        "layers": [("rain", {"level": 0.30, "hi": 6200}), ("street", {}),
                   ("roomtone", {"level": 0.20}), ("clock", {"level": 0.38})],
    },
    "study-room": {
        "desc": "Quiet room, ticking clock, HVAC. For focus/study loops.",
        "layers": [("roomtone", {"level": 0.20}), ("fan", {}),
                   ("clock", {"level": 0.30}), ("hiss", {"level": 0.025}),
                   ("hum", {})],
    },
    "night-forest": {
        "desc": "Crickets, soft wind, open air.",
        "layers": [("crickets", {}), ("wind", {"level": 0.22, "cutoff": 1100}),
                   ("roomtone", {"level": 0.10})],
    },
    "underwater": {
        "desc": "Submerged — moving water, bubbles rising, muffled depth.",
        "layers": [("current", {"level": 0.40, "cutoff": 780, "lo": 150,
                                "depth": 0.26}),
                   ("swish", {"level": 0.17, "lo": 260, "hi": 1100}),
                   ("bubbles", {"level": 0.05, "fizz": 0.05}),
                   ("waves", {"level": 0.11, "swell": 17.3, "lo": 190,
                              "hi": 1300})],
    },
    "underwater-soft": {
        "desc": "Underwater, held right back. Built to sit under music.",
        "layers": [("current", {"level": 0.30, "cutoff": 780, "lo": 150,
                                "depth": 0.18, "swell": 37}),
                   ("swish", {"level": 0.11, "lo": 260, "hi": 1100,
                              "period": 8.9}),
                   ("bubbles", {"level": 0.06, "fizz": 0.05}),
                   ("waves", {"level": 0.07, "swell": 23.1, "lo": 190,
                              "hi": 1300})],
    },
    "ocean-night": {
        "desc": "Swell and wind on a dark beach.",
        "layers": [("waves", {}), ("wind", {"level": 0.20}),
                   ("roomtone", {"level": 0.10})],
    },
}


def build_graph(preset_name, dur, extra_layers=None, master_db=6.0,
                fade_in=10, fade_out=25, music=None, music_level=0.55,
                sfx=None, sfx_level=0.8):
    """Assemble the full ambience filtergraph."""
    sp = SeedPool()
    chunks, labels = [], []

    spec = list(PRESETS[preset_name]["layers"]) if preset_name else []
    for name, params in (extra_layers or []):
        spec = [(n, p) for n, p in spec if n != name] + [(name, params)]

    for i, (name, params) in enumerate(spec):
        if name not in LAYERS:
            raise SystemExit(f"unknown layer '{name}'. known: {', '.join(sorted(LAYERS))}")
        chain, lbl = LAYERS[name](sp, dur, f"L{i}_{name}", **params)
        chunks.append(chain)
        labels.append(lbl)

    if not labels:
        raise SystemExit("no ambience layers selected")

    mix_in = "".join(f"[{l}]" for l in labels)
    n = len(labels)
    tail = (f"{mix_in}amix=inputs={n}:duration=first:normalize=0,"
            f"volume={master_db}dB,"
            f"highpass=f=28:poles=1,lowpass=f=12000:poles=1")

    if sfx:
        # A one-cycle strike track, looped. Because the cycle is the video's
        # own loop length, real strikes stay locked to the lightning for as
        # long as the render runs — 8 hours costs no more filtergraph than 8
        # minutes, which placing every hit individually would not survive.
        path = str(sfx).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        chunks.append(
            f"amovie=filename='{path}':loop=0,asetpts=N/SR/TB,"
            f"aformat=channel_layouts=stereo:sample_rates=48000,"
            f"atrim=0:{dur},volume={sfx_level}[SFX]"
        )
        tail = f"{tail}[AMBX];[AMBX][SFX]amix=inputs=2:duration=first:normalize=0"

    if music:
        # amovie with loop=0 repeats the (pre-seamed) music unit indefinitely.
        path = str(music).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        chunks.append(
            f"amovie=filename='{path}':loop=0,asetpts=N/SR/TB,"
            f"aformat=channel_layouts=stereo:sample_rates=48000,"
            f"atrim=0:{dur},volume={music_level}[MUSIC]"
        )
        tail = f"{tail}[AMB];[AMB][MUSIC]amix=inputs=2:duration=first:normalize=0"

    tail += (f",alimiter=level_in=1:level_out=1:limit=0.85:attack=5:release=120,"
             f"afade=t=in:st=0:d={fade_in},"
             f"afade=t=out:st={max(0, float(dur) - fade_out)}:d={fade_out}[aout]")

    chunks.append(tail)
    return ";".join(chunks)
