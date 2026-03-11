"""
Procedurally generated instrument samples.

Generates waveforms in memory as signed 16-bit PCM at a base frequency.
These get embedded directly into the IT file as sample data.
The tracker engine handles pitch-shifting to play different notes.
"""

import math
import random as _rng
import struct

# Base sample rate for all generated waveforms
SAMPLE_RATE = 44100

# Base note for samples: C-5 (MIDI 60). The tracker transposes from here.
BASE_NOTE_HZ = 261.63  # C4 in concert pitch


def _pack_samples(samples: list[int]) -> bytes:
    """Pack a list of signed 16-bit integer samples to bytes."""
    return struct.pack(f"<{len(samples)}h", *samples)


def _normalize(samples: list[float], amplitude: float = 0.9) -> list[int]:
    """Normalize float samples to signed 16-bit range."""
    peak = max(abs(s) for s in samples) if samples else 1.0
    if peak == 0:
        peak = 1.0
    scale = 32767 * amplitude / peak
    return [max(-32768, min(32767, int(s * scale))) for s in samples]


def square_wave(duty: float = 0.5, cycles: int = 4) -> tuple[bytes, int]:
    """Generate a square/pulse wave. duty=0.5 is classic square."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        samples.append(1.0 if phase < duty else -1.0)
    data = _pack_samples(_normalize(samples))
    return data, length


def sawtooth_wave(cycles: int = 4) -> tuple[bytes, int]:
    """Generate a sawtooth wave — good for bass and pads."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        samples.append(2.0 * phase - 1.0)
    data = _pack_samples(_normalize(samples))
    return data, length


def triangle_wave(cycles: int = 4) -> tuple[bytes, int]:
    """Generate a triangle wave — soft, mellow tone."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        if phase < 0.25:
            val = phase * 4.0
        elif phase < 0.75:
            val = 2.0 - phase * 4.0
        else:
            val = phase * 4.0 - 4.0
        samples.append(val)
    data = _pack_samples(_normalize(samples))
    return data, length


def sine_wave(cycles: int = 4) -> tuple[bytes, int]:
    """Generate a sine wave — clean sub bass."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        samples.append(math.sin(2.0 * math.pi * phase))
    data = _pack_samples(_normalize(samples))
    return data, length


def noise_white(length: int = 4000) -> tuple[bytes, int]:
    """Generate white noise — hi-hats, snare body."""

    samples = [_rng.uniform(-1.0, 1.0) for _ in range(length)]
    data = _pack_samples(_normalize(samples, amplitude=0.8))
    return data, length


def noise_periodic(period: int = 32, length: int = 4000) -> tuple[bytes, int]:
    """Generate periodic noise (looped short noise) — metallic, NES-like."""

    one_period = [_rng.uniform(-1.0, 1.0) for _ in range(period)]
    samples = []
    for i in range(length):
        samples.append(one_period[i % period])
    data = _pack_samples(_normalize(samples, amplitude=0.7))
    return data, length


def kick_drum(length: int = 3000) -> tuple[bytes, int]:
    """Synthesize a kick drum — pitch-dropping sine with noise burst."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Pitch drops from 150Hz to 40Hz
        freq = 150.0 * math.exp(-30.0 * t) + 40.0
        phase = 2.0 * math.pi * freq * t
        # Envelope: quick attack, medium decay
        env = math.exp(-8.0 * t)
        val = math.sin(phase) * env
        # Add noise click at start
        if i < 200:
        
            val += _rng.uniform(-0.3, 0.3) * (1.0 - i / 200.0)
        samples.append(val)
    data = _pack_samples(_normalize(samples))
    return data, length


def snare_drum(length: int = 4000) -> tuple[bytes, int]:
    """Synthesize a snare — sine body + noise."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Tone body at ~180Hz
        tone = math.sin(2.0 * math.pi * 180.0 * t) * math.exp(-20.0 * t)
        # Noise body
        noise = _rng.uniform(-1.0, 1.0) * math.exp(-10.0 * t)
        samples.append(tone * 0.4 + noise * 0.6)
    data = _pack_samples(_normalize(samples))
    return data, length


def hihat(length: int = 2000) -> tuple[bytes, int]:
    """Synthesize a hi-hat — filtered noise burst."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        noise = _rng.uniform(-1.0, 1.0)
        env = math.exp(-40.0 * t)
        samples.append(noise * env)
    data = _pack_samples(_normalize(samples, amplitude=0.6))
    return data, length


def tom_drum(length: int = 3500) -> tuple[bytes, int]:
    """Synthesize a tom — pitched sine with medium decay."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Pitch drops from 200Hz to 80Hz
        freq = 200.0 * math.exp(-15.0 * t) + 80.0
        phase = 2.0 * math.pi * freq * t
        env = math.exp(-6.0 * t)
        val = math.sin(phase) * env
        samples.append(val)
    data = _pack_samples(_normalize(samples))
    return data, length


def crash_cymbal(length: int = 8000) -> tuple[bytes, int]:
    """Synthesize a crash cymbal — layered noise with long decay."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Mix of noise frequencies for metallic character
        noise = _rng.uniform(-1.0, 1.0)
        shimmer = math.sin(2.0 * math.pi * 3200.0 * t) * 0.3
        env = math.exp(-4.0 * t)
        samples.append((noise * 0.7 + shimmer) * env)
    data = _pack_samples(_normalize(samples, amplitude=0.7))
    return data, length


def open_hihat(length: int = 5000) -> tuple[bytes, int]:
    """Synthesize an open hi-hat — noise with longer decay than closed."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        noise = _rng.uniform(-1.0, 1.0)
        env = math.exp(-8.0 * t)
        samples.append(noise * env)
    data = _pack_samples(_normalize(samples, amplitude=0.55))
    return data, length


# ── DSP utilities ──

def _lowpass(samples: list[float], cutoff_ratio: float = 0.3) -> list[float]:
    """Simple one-pole low-pass filter. cutoff_ratio 0.0-1.0 (lower = darker)."""
    alpha = max(0.001, min(1.0, cutoff_ratio))
    out = []
    prev = 0.0
    for s in samples:
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


def _lowpass_sweep(samples: list[float], start: float = 0.05,
                   end: float = 0.8) -> list[float]:
    """Low-pass filter with sweeping cutoff — opens up over time."""
    out = []
    prev = 0.0
    n = len(samples)
    for i, s in enumerate(samples):
        t = i / max(1, n - 1)
        alpha = start + (end - start) * t
        alpha = max(0.001, min(1.0, alpha))
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


def _distort(samples: list[float], drive: float = 3.0) -> list[float]:
    """Waveshaping distortion — soft clipping with adjustable drive."""
    return [math.tanh(s * drive) for s in samples]


def _reverb_tail(samples: list[float], decay: float = 0.4,
                 delay_ms: float = 15.0) -> list[float]:
    """Simple comb-filter reverb tail for drums."""
    delay_samples = int(SAMPLE_RATE * delay_ms / 1000.0)
    out = list(samples)
    for i in range(delay_samples, len(out)):
        out[i] += out[i - delay_samples] * decay
    # Second tap for density
    delay2 = int(delay_samples * 1.37)
    for i in range(delay2, len(out)):
        out[i] += out[i - delay2] * decay * 0.5
    return out


# ── Extended waveforms ──

def pwm_sweep(cycles: int = 8) -> tuple[bytes, int]:
    """Pulse width modulation sweep — duty cycle oscillates for rich movement."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        # Duty sweeps from 0.15 to 0.50 over the sample
        t = i / length
        duty = 0.15 + 0.35 * (0.5 + 0.5 * math.sin(2.0 * math.pi * 2.0 * t))
        samples.append(1.0 if phase < duty else -1.0)
    data = _pack_samples(_normalize(samples))
    return data, length


def supersaw(cycles: int = 4, num_saws: int = 5,
             detune: float = 0.015) -> tuple[bytes, int]:
    """Stacked detuned sawtooth waves — thick, chorus-like pad sound."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    # Create slightly detuned frequencies
    freqs = []
    for j in range(num_saws):
        offset = (j - num_saws // 2) * detune
        freqs.append(BASE_NOTE_HZ * (1.0 + offset))
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        val = 0.0
        for freq in freqs:
            phase = (t * freq) % 1.0
            val += 2.0 * phase - 1.0
        samples.append(val / num_saws)
    data = _pack_samples(_normalize(samples))
    return data, length


def filtered_saw(cycles: int = 4, cutoff: float = 0.25) -> tuple[bytes, int]:
    """Low-pass filtered sawtooth — warm, muted tone."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        raw.append(2.0 * phase - 1.0)
    samples = _lowpass(raw, cutoff)
    data = _pack_samples(_normalize(samples))
    return data, length


def sweep_pad(cycles: int = 8) -> tuple[bytes, int]:
    """Sawtooth with filter sweep — opens up over the sample duration."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        raw.append(2.0 * phase - 1.0)
    samples = _lowpass_sweep(raw, start=0.03, end=0.6)
    data = _pack_samples(_normalize(samples))
    return data, length


def distorted_bass(cycles: int = 4, drive: float = 4.0) -> tuple[bytes, int]:
    """Overdriven sawtooth bass — gritty Genesis-style."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        raw.append(2.0 * phase - 1.0)
    samples = _distort(raw, drive)
    # Roll off the harshest highs
    samples = _lowpass(samples, 0.5)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_organ(cycles: int = 6) -> tuple[bytes, int]:
    """3-operator FM — warm organ-like tone (algorithm: parallel modulators)."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # Op1: modulator at 2x (bright partial)
        mod1 = 1.5 * math.sin(2.0 * phase)
        # Op2: modulator at 3x (bell partial)
        mod2 = 0.8 * math.sin(3.0 * phase)
        # Carrier with both modulators summed
        carrier = math.sin(phase + mod1 + mod2)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_brass(cycles: int = 6) -> tuple[bytes, int]:
    """3-operator FM brass — punchy attack, mellows out."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # High modulation at attack, decays quickly
        mod_env = 6.0 * math.exp(-12.0 * t) + 1.0
        mod1 = mod_env * math.sin(1.0 * phase)
        mod2 = (mod_env * 0.5) * math.sin(3.0 * phase)
        carrier = math.sin(phase + mod1 + mod2)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_pad(cycles: int = 10) -> tuple[bytes, int]:
    """4-operator FM pad — lush, evolving texture."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # Slow LFO modulates the modulation depth
        lfo = 0.5 + 0.5 * math.sin(2.0 * math.pi * 3.0 * t)
        mod1 = (1.0 + lfo) * math.sin(2.0 * phase)
        mod2 = 0.6 * math.sin(3.0 * phase + mod1 * 0.3)
        mod3 = 0.4 * math.sin(5.0 * phase) * lfo
        carrier = math.sin(phase + mod1 + mod2 + mod3)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


# ── Enhanced drums ──

def kick_layered(length: int = 3500) -> tuple[bytes, int]:
    """Layered kick — sine body + click transient + sub."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Sub body: deep sine that drops
        freq = 160.0 * math.exp(-35.0 * t) + 35.0
        sub = math.sin(2.0 * math.pi * freq * t) * math.exp(-7.0 * t)
        # Click transient: short burst of higher harmonics
        click = 0.0
        if i < 150:
            click_env = (1.0 - i / 150.0) ** 2
            click = math.sin(2.0 * math.pi * 2500.0 * t) * click_env * 0.4
            click += math.sin(2.0 * math.pi * 4000.0 * t) * click_env * 0.2
        # Noise punch
        noise = 0.0
        if i < 100:
            noise = _rng.uniform(-0.25, 0.25) * (1.0 - i / 100.0)
        samples.append(sub + click + noise)
    data = _pack_samples(_normalize(samples))
    return data, length


def snare_layered(length: int = 5000) -> tuple[bytes, int]:
    """Layered snare — body + noise + wire rattle."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Tone body: two pitches for thickness
        tone1 = math.sin(2.0 * math.pi * 185.0 * t) * math.exp(-22.0 * t)
        tone2 = math.sin(2.0 * math.pi * 330.0 * t) * math.exp(-30.0 * t) * 0.3
        # Noise body
        noise = _rng.uniform(-1.0, 1.0) * math.exp(-9.0 * t)
        # Wire rattle: filtered noise with slower decay
        wire = _rng.uniform(-0.5, 0.5) * math.exp(-5.0 * t) * 0.3
        samples.append(tone1 * 0.35 + tone2 * 0.15 + noise * 0.5 + wire)
    # Add reverb tail
    float_samples = [s for s in samples]
    float_samples = _reverb_tail(float_samples, decay=0.25, delay_ms=12.0)
    data = _pack_samples(_normalize(float_samples))
    return data, len(float_samples)


def hihat_metallic(length: int = 2500) -> tuple[bytes, int]:
    """Metallic hi-hat — layered square noise + ring mod for shimmer."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Multiple high-frequency square waves for metallic character
        s1 = 1.0 if math.sin(2.0 * math.pi * 4500.0 * t) > 0 else -1.0
        s2 = 1.0 if math.sin(2.0 * math.pi * 6000.0 * t) > 0 else -1.0
        s3 = 1.0 if math.sin(2.0 * math.pi * 7800.0 * t) > 0 else -1.0
        # Ring modulate them together
        metallic = s1 * s2 * s3
        env = math.exp(-45.0 * t)
        samples.append(metallic * env)
    data = _pack_samples(_normalize(samples, amplitude=0.6))
    return data, length


# FM synthesis — the Genesis sound
def fm_bell(cycles: int = 8) -> tuple[bytes, int]:
    """FM synthesis bell tone — classic Genesis/YM2612 sound."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    mod_ratio = 3.0  # Modulator frequency ratio
    mod_index = 2.5  # Modulation depth
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        modulator = mod_index * math.sin(mod_ratio * phase)
        carrier = math.sin(phase + modulator)
        # Gentle decay
        env = math.exp(-1.5 * t)
        samples.append(carrier * env)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_bass(cycles: int = 4) -> tuple[bytes, int]:
    """FM synthesis bass — punchy Genesis bass sound."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    mod_ratio = 1.0
    mod_index = 5.0
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # Modulation index decays for punch
        mod_env = mod_index * math.exp(-8.0 * t)
        modulator = mod_env * math.sin(mod_ratio * phase)
        carrier = math.sin(phase + modulator)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_lead(cycles: int = 6) -> tuple[bytes, int]:
    """FM synthesis lead — bright, cutting Genesis lead."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    mod_ratio = 2.0
    mod_index = 3.0
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        modulator = mod_index * math.sin(mod_ratio * phase)
        carrier = math.sin(phase + modulator)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


# Instrument presets: (name, generator_func, kwargs, default_volume)
INSTRUMENT_PRESETS = {
    # Melodic — classic
    "square_lead":    (square_wave,    {"duty": 0.5},  64),
    "pulse_lead":     (square_wave,    {"duty": 0.25}, 64),
    "saw_lead":       (sawtooth_wave,  {},             58),
    "triangle_lead":  (triangle_wave,  {},             64),
    "fm_bell":        (fm_bell,        {},             50),
    "fm_lead":        (fm_lead,        {},             58),
    # Melodic — extended
    "pwm_lead":       (pwm_sweep,      {},             60),
    "supersaw_lead":  (supersaw,       {},             52),
    "filtered_lead":  (filtered_saw,   {"cutoff": 0.4}, 58),
    "sweep_lead":     (sweep_pad,      {},             48),
    "fm_organ":       (fm_organ,       {},             52),
    "fm_brass":       (fm_brass,       {},             58),
    "fm_pad":         (fm_pad,         {},             44),
    # Bass — classic
    "saw_bass":       (sawtooth_wave,  {},             64),
    "triangle_bass":  (triangle_wave,  {},             64),
    "sine_bass":      (sine_wave,      {},             64),
    "fm_bass":        (fm_bass,        {},             64),
    "square_bass":    (square_wave,    {"duty": 0.5},  58),
    # Bass — extended
    "distorted_bass": (distorted_bass, {},             62),
    "filtered_bass":  (filtered_saw,   {"cutoff": 0.2}, 64),
    "supersaw_bass":  (supersaw,       {"detune": 0.008}, 58),
    # Drums — classic
    "kick":           (kick_drum,      {},             64),
    "snare":          (snare_drum,     {},             56),
    "hihat":          (hihat,          {},             40),
    "tom":            (tom_drum,       {},             56),
    "crash":          (crash_cymbal,   {},             48),
    "open_hihat":     (open_hihat,     {},             38),
    "noise":          (noise_white,    {},             32),
    # Drums — enhanced
    "kick_layered":   (kick_layered,   {},             64),
    "snare_layered":  (snare_layered,  {},             56),
    "hihat_metallic": (hihat_metallic, {},             40),
}


def generate_instrument(name: str) -> tuple[bytes, int, int]:
    """Generate a named instrument. Returns (pcm_data, length, default_volume)."""
    if name not in INSTRUMENT_PRESETS:
        raise ValueError(f"Unknown instrument: {name}")
    func, kwargs, vol = INSTRUMENT_PRESETS[name]
    data, length = func(**kwargs)
    return data, length, vol
