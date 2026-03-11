"""
Procedurally generated instrument samples.

Generates waveforms in memory as signed 16-bit PCM at a base frequency.
These get embedded directly into the IT file as sample data.
The tracker engine handles pitch-shifting to play different notes.
"""

import math
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
    import random as _rng
    samples = [_rng.uniform(-1.0, 1.0) for _ in range(length)]
    data = _pack_samples(_normalize(samples, amplitude=0.8))
    return data, length


def noise_periodic(period: int = 32, length: int = 4000) -> tuple[bytes, int]:
    """Generate periodic noise (looped short noise) — metallic, NES-like."""
    import random as _rng
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
            import random as _rng
            val += _rng.uniform(-0.3, 0.3) * (1.0 - i / 200.0)
        samples.append(val)
    data = _pack_samples(_normalize(samples))
    return data, length


def snare_drum(length: int = 4000) -> tuple[bytes, int]:
    """Synthesize a snare — sine body + noise."""
    import random as _rng
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
    import random as _rng
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        noise = _rng.uniform(-1.0, 1.0)
        env = math.exp(-40.0 * t)
        samples.append(noise * env)
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
    # Melodic
    "square_lead":    (square_wave,    {"duty": 0.5},  64),
    "pulse_lead":     (square_wave,    {"duty": 0.25}, 64),
    "saw_lead":       (sawtooth_wave,  {},             58),
    "triangle_lead":  (triangle_wave,  {},             64),
    "fm_bell":        (fm_bell,        {},             50),
    "fm_lead":        (fm_lead,        {},             58),
    # Bass
    "saw_bass":       (sawtooth_wave,  {},             64),
    "triangle_bass":  (triangle_wave,  {},             64),
    "sine_bass":      (sine_wave,      {},             64),
    "fm_bass":        (fm_bass,        {},             64),
    "square_bass":    (square_wave,    {"duty": 0.5},  58),
    # Drums
    "kick":           (kick_drum,      {},             64),
    "snare":          (snare_drum,     {},             56),
    "hihat":          (hihat,          {},             40),
    "noise":          (noise_white,    {},             32),
}


def generate_instrument(name: str) -> tuple[bytes, int, int]:
    """Generate a named instrument. Returns (pcm_data, length, default_volume)."""
    if name not in INSTRUMENT_PRESETS:
        raise ValueError(f"Unknown instrument: {name}")
    func, kwargs, vol = INSTRUMENT_PRESETS[name]
    data, length = func(**kwargs)
    return data, length, vol
