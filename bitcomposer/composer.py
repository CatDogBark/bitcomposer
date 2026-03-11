"""
Procedural song composer.

Generates complete songs by combining music theory, instrument samples,
and pattern generation into playable Impulse Tracker modules.
"""

import random

from . import theory
from . import samples as smp
from . import structure as struct
from .it_format import (
    ITSample, ITPattern, ITNote, midi_to_it_note, NOTE_CUT, NOTE_OFF,
    write_it_file,
    FX_VIBRATO, FX_PORTAMENTO, FX_VOLUME_SLIDE, FX_TREMOLO, FX_SET_TEMPO,
)


# Channel assignments
CH_MELODY = 0
CH_HARMONY = 1
CH_HARMONY2 = 2
CH_HARMONY3 = 3
CH_BASS = 4
CH_ARP = 5
CH_KICK = 6
CH_SNARE = 7
CH_HIHAT = 8
CH_TOM = 9
CH_CRASH = 10
CH_OPEN_HAT = 11

NUM_CHANNELS = 12
ROWS_PER_PATTERN = 64
STEPS_PER_ROW = 4  # 16 steps = 64 rows / 4 rows per step


def _pick_instruments(prefer_fm: bool | None = None,
                      bass_weight: str = "heavy") -> dict[str, str]:
    """Pick a random instrument set for the song."""
    if prefer_fm is True:
        lead_choices = ["fm_lead", "fm_lead", "fm_bell", "fm_brass", "fm_organ"]
        harmony_choices = ["fm_pad", "fm_bell", "fm_organ", "sweep_lead"]
        bass_heavy = ["fm_bass", "fm_bass", "distorted_bass", "filtered_bass"]
        bass_medium = ["fm_bass", "filtered_bass", "saw_bass"]
        bass_light = ["pluck_bass", "thin_bass", "bright_bass"]
        arp_choices = ["fm_bell", "fm_lead", "fm_brass"]
    elif prefer_fm is False:
        lead_choices = ["square_lead", "pulse_lead", "triangle_lead", "saw_lead",
                        "pwm_lead", "filtered_lead"]
        harmony_choices = ["triangle_lead", "square_lead", "pulse_lead",
                           "supersaw_lead", "sweep_lead"]
        bass_heavy = ["triangle_bass", "sine_bass", "square_bass", "saw_bass",
                      "filtered_bass"]
        bass_medium = ["square_bass", "triangle_bass", "filtered_bass"]
        bass_light = ["pluck_bass", "thin_bass", "bright_bass"]
        arp_choices = ["square_lead", "pulse_lead", "triangle_lead", "pwm_lead"]
    else:
        lead_choices = ["square_lead", "pulse_lead", "saw_lead", "fm_lead", "fm_bell",
                        "pwm_lead", "supersaw_lead", "fm_brass", "filtered_lead"]
        harmony_choices = ["triangle_lead", "square_lead", "fm_bell", "pulse_lead",
                           "fm_pad", "supersaw_lead", "sweep_lead", "fm_organ"]
        bass_heavy = ["saw_bass", "triangle_bass", "fm_bass", "sine_bass",
                      "square_bass", "distorted_bass", "filtered_bass", "supersaw_bass"]
        bass_medium = ["saw_bass", "fm_bass", "square_bass", "filtered_bass"]
        bass_light = ["pluck_bass", "thin_bass", "bright_bass"]
        arp_choices = ["square_lead", "pulse_lead", "fm_bell", "triangle_lead",
                       "pwm_lead", "fm_brass"]

    # Pick bass timbre based on weight
    if bass_weight == "light":
        bass_choices = bass_light
    elif bass_weight == "medium":
        bass_choices = bass_medium
    else:
        bass_choices = bass_heavy

    lead = random.choice(lead_choices)
    harmony = random.choice([h for h in harmony_choices if h != lead] or harmony_choices)
    bass = random.choice(bass_choices)
    arp = random.choice([a for a in arp_choices if a != lead] or arp_choices)

    # Enhanced drums: 40% chance of using layered drums
    use_layered_drums = random.random() < 0.4

    return {
        "melody": lead,
        "harmony": harmony,
        "bass": bass,
        "arp": arp,
        "kick": "kick_layered" if use_layered_drums else "kick",
        "snare": "snare_layered" if use_layered_drums else "snare",
        "hihat": "hihat_metallic" if use_layered_drums else "hihat",
        "tom": "tom",
        "crash": "crash",
        "open_hihat": "open_hihat",
    }


def _build_samples(instruments: dict[str, str]) -> list[ITSample]:
    """Generate ITSample objects for all instruments."""
    samples = []
    seen = {}
    sample_map = {}  # instrument_key -> sample index (1-based)

    for key, name in instruments.items():
        if name in seen:
            sample_map[key] = seen[name]
            continue

        data, length, vol = smp.generate_instrument(name)

        # Drums don't loop
        is_drum = key in ("kick", "snare", "hihat", "tom", "crash", "open_hihat")

        it_sample = ITSample(
            name=name.replace("_", " ").title(),
            filename=name[:12],
            data=data,
            length=length,
            loop=not is_drum,
            loop_start=0,
            loop_end=length,
            default_volume=vol,
            c5_speed=smp.SAMPLE_RATE,
        )
        samples.append(it_sample)
        idx = len(samples)  # 1-based
        seen[name] = idx
        sample_map[key] = idx

    return samples, sample_map


def _generate_melody_simple(scale_notes: list[int], chord_notes: list[int],
                            rows: int, density: float = 0.5) -> list[tuple[int, int]]:
    """Generate a simple random-walk melody. Returns [(row, midi_note), ...]."""
    notes = []
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return notes

    chord_in_range = [n for n in chord_notes if n in melody_notes]
    current = random.choice(chord_in_range) if chord_in_range else random.choice(melody_notes)

    row = 0
    while row < rows:
        if random.random() < density:
            idx = melody_notes.index(current) if current in melody_notes else 0
            step = random.choices([-2, -1, 0, 1, 2], weights=[10, 25, 15, 25, 10], k=1)[0]
            new_idx = max(0, min(len(melody_notes) - 1, idx + step))
            current = melody_notes[new_idx]
            if random.random() < 0.2 and chord_in_range:
                current = random.choice(chord_in_range)
            duration = random.choice([2, 4, 4, 4, 8])
            notes.append((row, current))
            row += duration
        else:
            row += random.choice([2, 4])

    return notes


# ── Motif-based melody system ──

# Rhythmic templates: list of row offsets within a 32-row half-phrase
RHYTHM_TEMPLATES = [
    [0, 4, 8, 12],                     # Quarter notes
    [0, 4, 8, 14],                     # Dotted ending
    [0, 4, 6, 8, 12],                  # Eighth note pickup
    [0, 2, 8, 12, 16],                 # Syncopated
    [0, 8, 12, 14],                    # Long-short-short
    [0, 4, 8, 10, 12],                 # Running then rest
    [0, 6, 8, 12, 14],                 # Off-beat accent
    [0, 4, 12, 14, 16],               # Gap then flurry
]

# Contour shapes: relative direction for each note in a motif
# Values are scale steps from starting note — wider intervals = more melodic movement
CONTOURS = {
    # Cumulative: each value is a step from current position
    "arch":        [0, 2, 2, -2, -2],       # Rise then fall
    "descent":     [0, -1, -2, -2, 1],      # Stepwise fall, partial recover
    "climb":       [0, 1, 2, 2, -1],        # Gradual rise, step back
    "valley":      [0, -2, -2, 2, 2],       # Dip then return
    "leap_return": [0, 4, -1, -1, -2],      # Big jump, walk back down
    "zigzag":      [0, 3, -4, 3, -2],       # Alternating leaps
    "cascade":     [0, -3, 2, -3, 1],       # Falling with rebounds
    "soar":        [0, 2, 3, 1, -2],        # Big climb then relax
}


def _generate_motif(length: int = 4) -> dict:
    """Generate a rhythmic+melodic motif template."""
    rhythm = random.choice(RHYTHM_TEMPLATES)
    # Trim or extend to match length
    if len(rhythm) > length:
        rhythm = rhythm[:length]
    elif len(rhythm) < length:
        # Add notes at end
        last = rhythm[-1]
        while len(rhythm) < length:
            last += random.choice([2, 4])
            rhythm.append(last)

    contour_name = random.choice(list(CONTOURS.keys()))
    contour = CONTOURS[contour_name]

    # Scale contour to motif length
    if len(contour) != len(rhythm):
        # Interpolate contour to match rhythm length
        scaled = []
        for i in range(len(rhythm)):
            src = i * (len(contour) - 1) / max(1, len(rhythm) - 1)
            lo = int(src)
            hi = min(lo + 1, len(contour) - 1)
            frac = src - lo
            val = contour[lo] * (1 - frac) + contour[hi] * frac
            scaled.append(round(val))
        contour = scaled

    return {
        "rhythm": rhythm,
        "contour": contour,
        "contour_name": contour_name,
    }


def _vary_motif(motif: dict, amount: float = 0.3) -> dict:
    """Create a variation of a motif — small rhythmic/melodic changes."""
    rhythm = list(motif["rhythm"])
    contour = list(motif["contour"])

    for i in range(len(rhythm)):
        if random.random() < amount:
            # Slight rhythmic shift
            rhythm[i] = max(0, rhythm[i] + random.choice([-2, 0, 2]))

    for i in range(len(contour)):
        if random.random() < amount:
            contour[i] += random.choice([-1, 0, 1])

    # Keep rhythm sorted and non-negative
    rhythm.sort()
    rhythm[0] = 0

    return {"rhythm": rhythm, "contour": contour, "contour_name": motif["contour_name"]}


def _realize_motif(motif: dict, scale_notes: list[int],
                   chord_notes: list[int], start_row: int,
                   start_note_idx: int, resolve_to_chord: bool = False,
                   rows: int = 64) -> tuple[list[tuple[int, int]], int]:
    """
    Realize a motif into actual notes.

    Returns (note_list, ending_note_idx) where note_list is [(row, midi_note), ...].
    If resolve_to_chord is True, the last note snaps to a chord tone.
    """
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return [], start_note_idx

    chord_in_range = [n for n in chord_notes if n in melody_notes]

    notes = []
    current_idx = max(0, min(len(melody_notes) - 1, start_note_idx))

    for i, (row_offset, direction) in enumerate(zip(motif["rhythm"], motif["contour"])):
        row = start_row + row_offset
        if row >= rows:
            break

        # Contour is cumulative — each step moves from current position
        target_idx = current_idx + direction
        target_idx = max(0, min(len(melody_notes) - 1, target_idx))

        # If we hit a boundary and would repeat the same note, nudge the other way
        if target_idx == current_idx and direction != 0:
            nudge = 1 if current_idx < len(melody_notes) // 2 else -1
            target_idx = max(0, min(len(melody_notes) - 1, current_idx + nudge))

        # Last note: resolve to chord tone if requested
        if resolve_to_chord and i == len(motif["rhythm"]) - 1 and chord_in_range:
            # Find nearest chord tone
            closest = min(chord_in_range, key=lambda n: abs(melody_notes.index(n) - target_idx)
                         if n in melody_notes else 999)
            if closest in melody_notes:
                target_idx = melody_notes.index(closest)

        current_idx = target_idx
        notes.append((row, melody_notes[current_idx]))

    return notes, current_idx


def _generate_melody_phrased(scale_notes: list[int], chord_notes: list[int],
                              rows: int, density: float = 0.5,
                              motif: dict | None = None,
                              is_answer: bool = False) -> list[tuple[int, int]]:
    """
    Generate a melody using motif-based phrase structure.

    Uses question-answer phrasing: first half is the "question" (ends on tension),
    second half is the "answer" (resolves to chord tone).
    """
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return []

    if motif is None:
        motif = _generate_motif(length=random.choice([4, 5]))

    chord_in_range = [n for n in chord_notes if n in melody_notes]

    # Pick starting note — vary the register to avoid always landing on same note
    # Spread across the range: sometimes start high, sometimes low
    range_third = len(melody_notes) // 3
    register = random.choice(["low", "mid", "high"])
    if register == "low":
        candidates = melody_notes[:range_third + 1]
    elif register == "high":
        candidates = melody_notes[-(range_third + 1):]
    else:
        candidates = melody_notes[range_third:2 * range_third + 1]

    # Prefer chord tones within the chosen register
    register_chord = [n for n in chord_in_range if n in candidates]
    if register_chord:
        start_note = random.choice(register_chord)
    elif candidates:
        start_note = random.choice(candidates)
    else:
        start_note = random.choice(melody_notes)
    start_idx = melody_notes.index(start_note)

    all_notes = []
    half = rows // 2

    # Question phrase: first half, doesn't resolve
    q_motif = motif if not is_answer else _vary_motif(motif, 0.2)
    q_notes, end_idx = _realize_motif(
        q_motif, scale_notes, chord_notes,
        start_row=0, start_note_idx=start_idx,
        resolve_to_chord=False, rows=half,
    )
    all_notes.extend(q_notes)

    # Rest gap between phrases (density-dependent)
    gap = 4 if density > 0.5 else 8

    # Answer phrase: second half, resolves to chord tone
    a_motif = _vary_motif(motif, 0.3)
    a_notes, _ = _realize_motif(
        a_motif, scale_notes, chord_notes,
        start_row=half + gap, start_note_idx=end_idx,
        resolve_to_chord=True, rows=rows,
    )
    all_notes.extend(a_notes)

    # Add passing tones between phrases based on density
    if density > 0.5 and len(all_notes) > 0:
        # Fill sparse gaps with occasional passing notes
        filled = list(all_notes)
        for i in range(len(all_notes) - 1):
            row_a, note_a = all_notes[i]
            row_b, note_b = all_notes[i + 1]
            gap_rows = row_b - row_a
            if gap_rows >= 8 and random.random() < density - 0.3:
                # Insert a passing note halfway
                mid_row = row_a + gap_rows // 2
                if note_a in melody_notes and note_b in melody_notes:
                    idx_a = melody_notes.index(note_a)
                    idx_b = melody_notes.index(note_b)
                    mid_idx = (idx_a + idx_b) // 2
                    mid_idx = max(0, min(len(melody_notes) - 1, mid_idx))
                    filled.append((mid_row, melody_notes[mid_idx]))
        all_notes = sorted(filled, key=lambda x: x[0])

    return all_notes


def _generate_melody(scale_notes: list[int], chord_notes: list[int],
                     rows: int, density: float = 0.5,
                     motif: dict | None = None,
                     is_answer: bool = False,
                     phrased: bool = True) -> list[tuple[int, int]]:
    """Generate a melody line. Returns [(row, midi_note), ...]."""
    if phrased:
        return _generate_melody_phrased(
            scale_notes, chord_notes, rows, density, motif, is_answer)
    return _generate_melody_simple(scale_notes, chord_notes, rows, density)


# ── Harmony voicing system ──

HARMONY_VOICINGS = {
    "stabs": {
        "description": "Short chord stabs every 16 rows",
        "interval": 16,
        "sustain": False,
    },
    "sustain": {
        "description": "Sustained pad chords, held across the pattern",
        "interval": 32,
        "sustain": True,
    },
    "rhythmic": {
        "description": "Rhythmic chord hits synced to groove",
        "interval": 8,
        "sustain": False,
    },
}


def _generate_harmony(chord_notes: list[int], rows: int,
                      voicing: str = "stabs",
                      num_voices: int = 2) -> list[list[tuple[int, int]]]:
    """
    Generate harmony parts for multiple channels.

    Returns a list of note lists, one per voice: [[(row, midi_note), ...], ...]
    Voice 0 = highest, Voice N = lowest (within the chord voicing range).
    """
    # Get voicing config
    config = HARMONY_VOICINGS.get(voicing, HARMONY_VOICINGS["stabs"])
    interval = config["interval"]
    sustain = config["sustain"]

    # Build voiced chord notes in octave 4-5 range (MIDI 60-84)
    voiced = []
    for cn in chord_notes[:4]:  # Max 4 chord tones
        note = cn
        while note < 60:
            note += 12
        while note > 84:
            note -= 12
        voiced.append(note)
    voiced.sort()

    # Ensure we have enough voices
    num_voices = min(num_voices, len(voiced))
    if num_voices == 0:
        return []

    # Spread voices across available chord tones
    voice_notes = []
    if num_voices == 1:
        voice_notes = [voiced[0]]
    elif num_voices == 2:
        voice_notes = [voiced[0], voiced[-1]]
    else:
        # Pick evenly spaced tones
        step = max(1, len(voiced) // num_voices)
        for i in range(num_voices):
            idx = min(i * step, len(voiced) - 1)
            voice_notes.append(voiced[idx])

    # Generate note events for each voice
    result = []
    for voice_idx, base_note in enumerate(voice_notes):
        notes = []
        for row in range(0, rows, interval):
            # Add slight variation in timing for rhythmic feel
            actual_row = row
            if voicing == "rhythmic" and voice_idx > 0 and row % 16 == 8:
                # Offset higher voices slightly for strum effect
                actual_row = min(row + 1, rows - 1)

            notes.append((actual_row, base_note))

            # For sustained voicing, don't add note-off (let it ring)
            # For stabs, the next note or silence handles cutoff
        result.append(notes)

    return result


def _generate_counter_melody(scale_notes: list[int], chord_notes: list[int],
                              melody_notes_list: list[tuple[int, int]],
                              rows: int) -> list[tuple[int, int]]:
    """
    Generate a counter-melody that fills gaps in the main melody.

    Moves in contrary motion and plays in the rests between melody phrases.
    """
    melody_range = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_range:
        melody_range = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_range:
        return []

    chord_in_range = [n for n in chord_notes if n in melody_range]

    # Find gaps in the melody (rows where melody is silent)
    melody_rows = {row for row, _ in melody_notes_list}
    # Extend occupied rows to include duration estimates
    occupied = set()
    sorted_melody = sorted(melody_notes_list, key=lambda x: x[0])
    for i, (row, _) in enumerate(sorted_melody):
        next_row = sorted_melody[i + 1][0] if i + 1 < len(sorted_melody) else rows
        duration = min(next_row - row, 8)  # Assume max 8 row duration
        for r in range(row, row + duration):
            occupied.add(r)

    # Generate counter notes in the gaps
    notes = []
    # Start from a chord tone in the upper register
    if chord_in_range:
        current = random.choice(chord_in_range)
    else:
        current = melody_range[len(melody_range) // 2]

    row = 0
    while row < rows:
        if row not in occupied and random.random() < 0.4:
            # Find direction: move opposite to where melody was heading
            nearest_melody = None
            for mr, mn in sorted_melody:
                if mr > row:
                    nearest_melody = mn
                    break

            idx = melody_range.index(current) if current in melody_range else len(melody_range) // 2

            if nearest_melody and nearest_melody in melody_range:
                melody_idx = melody_range.index(nearest_melody)
                # Contrary motion: if melody goes up, counter goes down
                if melody_idx > idx:
                    step = random.choice([-1, -2])
                else:
                    step = random.choice([1, 2])
            else:
                step = random.choice([-1, 0, 1])

            new_idx = max(0, min(len(melody_range) - 1, idx + step))
            current = melody_range[new_idx]

            # Snap to chord tone occasionally
            if random.random() < 0.3 and chord_in_range:
                closest = min(chord_in_range,
                             key=lambda n: abs(melody_range.index(n) - new_idx)
                             if n in melody_range else 999)
                if closest in melody_range:
                    current = closest

            notes.append((row, current))
            row += random.choice([4, 4, 8])
        else:
            row += 2

    return notes


def _generate_bass(root: int, chord_type: str,
                   rows: int, style: str = "steady",
                   weight: str = "heavy") -> list[tuple[int, int]]:
    """Generate a bass line. Returns [(row, midi_note), ...]."""
    # Register depends on weight
    if weight == "light":
        # Octave 3-4 (MIDI 48-71) — punchier, more melodic
        bass_root = root
        while bass_root >= 60:
            bass_root -= 12
        while bass_root < 48:
            bass_root += 12
    elif weight == "medium":
        # Octave 3 (MIDI 42-59) — middle ground
        bass_root = root
        while bass_root >= 54:
            bass_root -= 12
        while bass_root < 42:
            bass_root += 12
    else:
        # Octave 2-3 (MIDI 36-59) — deep and heavy
        bass_root = root
        while bass_root >= 48:
            bass_root -= 12
        while bass_root < 36:
            bass_root += 12

    chord = theory.build_chord(bass_root, chord_type)
    notes = []

    # Sparser step sizes for lighter weights
    if weight == "light":
        step_scale = 2  # half as many notes
    elif weight == "medium":
        step_scale = 1.5
    else:
        step_scale = 1

    if style == "steady":
        step = int(8 * step_scale)
        for row in range(0, rows, step):
            notes.append((row, bass_root))
    elif style == "octave":
        step = int(4 * step_scale)
        for i, row in enumerate(range(0, rows, step)):
            if i % 2 == 0:
                notes.append((row, bass_root))
            else:
                notes.append((row, bass_root + 12))
    elif style == "walking":
        step = int(4 * step_scale)
        for i, row in enumerate(range(0, rows, step)):
            note = chord[i % len(chord)]
            notes.append((row, note))
    elif style == "driving":
        step = int(2 * step_scale)
        for row in range(0, rows, step):
            notes.append((row, bass_root))

    return notes


def _generate_arpeggio(chord_notes: list[int], rows: int,
                       style: str = "up") -> list[tuple[int, int]]:
    """Generate an arpeggio pattern. Returns [(row, midi_note), ...]."""
    # Arp in octave 4-5
    arp_notes = []
    for n in chord_notes:
        for octave_shift in [0, 12]:
            note = n + octave_shift
            if 48 <= note <= 84:
                arp_notes.append(note)
    arp_notes.sort()

    if not arp_notes:
        return []

    notes = []
    if style == "up":
        for i, row in enumerate(range(0, rows, 2)):
            notes.append((row, arp_notes[i % len(arp_notes)]))
    elif style == "down":
        arp_notes_rev = list(reversed(arp_notes))
        for i, row in enumerate(range(0, rows, 2)):
            notes.append((row, arp_notes_rev[i % len(arp_notes_rev)]))
    elif style == "updown":
        seq = arp_notes + list(reversed(arp_notes[1:-1])) if len(arp_notes) > 2 else arp_notes
        for i, row in enumerate(range(0, rows, 2)):
            notes.append((row, seq[i % len(seq)]))
    elif style == "random":
        for row in range(0, rows, 2):
            notes.append((row, random.choice(arp_notes)))

    return notes


def _generate_drums(drum_pattern: dict[str, list[int]],
                    rows: int) -> dict[str, list[int]]:
    """Expand a 16-step drum pattern to fill the given number of rows."""
    rows_per_step = rows // 16
    expanded = {}
    for drum, pattern in drum_pattern.items():
        hits = []
        for step, hit in enumerate(pattern):
            if hit:
                hits.append(step * rows_per_step)
        expanded[drum] = hits
    return expanded


def _humanize_volume(base_volume: int, amount: int = 6) -> int:
    """Add subtle random velocity variation to a note."""
    variation = random.randint(-amount, amount)
    return max(1, min(64, base_volume + variation))


def _apply_notes_to_pattern(pattern: ITPattern, channel: int,
                            note_list: list[tuple[int, int]],
                            instrument: int, volume: int = 255,
                            effect: int = 0, effect_val: int = 0,
                            humanize: bool = False):
    """Write note events into a pattern channel."""
    for row, midi_note in note_list:
        if 0 <= row < pattern.rows:
            it_note = midi_to_it_note(midi_note)
            vol = volume
            if humanize and vol != 255:
                vol = _humanize_volume(vol)
            pattern.data[row][channel] = ITNote(
                note=it_note,
                instrument=instrument,
                volume=vol,
                effect=effect,
                effect_val=effect_val,
            )


def _apply_vibrato(pattern: ITPattern, channel: int,
                   note_list: list[tuple[int, int]], speed: int = 4, depth: int = 3):
    """Add vibrato continuation to rows after note-on events."""
    vibrato_val = ((speed & 0x0F) << 4) | (depth & 0x0F)
    for i, (row, _) in enumerate(note_list):
        # Get duration until next note or end of pattern
        next_row = note_list[i + 1][0] if i + 1 < len(note_list) else pattern.rows
        # Add vibrato on rows after the note-on (note-on row already has effect from _apply_notes)
        for r in range(row + 1, min(next_row, pattern.rows)):
            if pattern.data[r][channel].note == 0:  # Don't overwrite note events
                pattern.data[r][channel] = ITNote(
                    effect=FX_VIBRATO,
                    effect_val=vibrato_val,
                )


def _apply_portamento(pattern: ITPattern, channel: int,
                      note_list: list[tuple[int, int]],
                      instrument: int, volume: int = 255,
                      porta_speed: int = 32, humanize: bool = False):
    """Write notes with tone portamento — slides between consecutive notes."""
    for i, (row, midi_note) in enumerate(note_list):
        if 0 <= row < pattern.rows:
            it_note = midi_to_it_note(midi_note)
            vol = volume
            if humanize and vol != 255:
                vol = _humanize_volume(vol)
            if i == 0:
                # First note: play normally
                pattern.data[row][channel] = ITNote(
                    note=it_note, instrument=instrument, volume=vol,
                )
            else:
                # Subsequent notes: slide to them
                pattern.data[row][channel] = ITNote(
                    note=it_note, instrument=instrument, volume=vol,
                    effect=FX_PORTAMENTO, effect_val=porta_speed,
                )


def _apply_fade(pattern: ITPattern, channel: int, fade_in: bool = False,
                fade_out: bool = False, rows_count: int = 8):
    """Add volume fade in/out at pattern start/end."""
    if fade_in:
        # Volume slide up over first N rows
        slide_val = 0x30  # Slide up by 3 per tick
        for r in range(min(rows_count, pattern.rows)):
            existing = pattern.data[r][channel]
            if existing.effect == 0:
                existing.effect = FX_VOLUME_SLIDE
                existing.effect_val = slide_val
    if fade_out:
        # Volume slide down over last N rows
        slide_val = 0x03  # Slide down by 3 per tick
        start = max(0, pattern.rows - rows_count)
        for r in range(start, pattern.rows):
            existing = pattern.data[r][channel]
            if existing.effect == 0:
                existing.effect = FX_VOLUME_SLIDE
                existing.effect_val = slide_val


def _apply_drums_to_pattern(pattern: ITPattern, drum_hits: dict[str, list[int]],
                            sample_map: dict[str, int],
                            swing: int = 0):
    """Write drum hits into pattern. swing=0-3 shifts off-beat hats late."""
    drum_channels = {
        "kick": CH_KICK, "snare": CH_SNARE, "hihat": CH_HIHAT,
        "hat": CH_HIHAT, "tom": CH_TOM, "crash": CH_CRASH,
        "open_hihat": CH_OPEN_HAT,
    }
    drum_note = midi_to_it_note(60)

    for drum, hits in drum_hits.items():
        ch = drum_channels.get(drum)
        inst_key = drum if drum != "hat" else "hihat"
        inst = sample_map.get(inst_key)
        if ch is None or inst is None:
            continue
        for row in hits:
            actual_row = row
            # Apply swing to off-beat hihat hits
            if swing > 0 and drum in ("hihat", "hat") and row % 8 == 4:
                actual_row = min(row + swing, pattern.rows - 1)
            if 0 <= actual_row < pattern.rows:
                pattern.data[actual_row][ch] = ITNote(
                    note=drum_note,
                    instrument=inst,
                )


def _pick_section_bass(bass_weight: str, section_energy: float,
                       bass_style: str) -> str:
    """Choose bass style for a section based on weight and energy."""
    if bass_weight == "light":
        if section_energy > 0.85:
            return random.choice(["steady", "walking"])
        return random.choice(["steady", "steady", "walking"])
    elif section_energy < 0.5:
        return random.choice(["steady", "steady"])
    elif section_energy > 0.85:
        return random.choice(["driving", "octave", bass_style])
    return bass_style


def _pick_section_motif(sec_type: str, use_phrased: bool,
                        chorus_motif, verse_motif, bridge_motif) -> dict | None:
    """Pick the appropriate motif for a section type."""
    if not use_phrased:
        return None
    if sec_type == "chorus":
        return chorus_motif
    elif sec_type == "verse":
        return verse_motif
    elif sec_type == "bridge":
        return bridge_motif
    else:
        return _generate_motif(length=random.choice([3, 4]))


def _compose_pattern(*, scale_notes, chord_root, chord_type, chord_notes,
                     layers, sec_type, section, section_energy, section_density,
                     section_bass, sample_map, samples,
                     melody_sample, use_phrased, section_motif,
                     chord_idx, is_answer,
                     voicing_style, num_harmony_voices,
                     vibrato_speed, vibrato_depth,
                     bass_weight, use_bass_porta, porta_speed,
                     arp_style, drum_pattern, drum_density,
                     fill_pattern, section_prog, is_ending, ending_style,
                     swing_amount, is_intro) -> ITPattern:
    """Compose a single pattern with all layers."""
    pat = ITPattern(rows=ROWS_PER_PATTERN, channels=NUM_CHANNELS)
    melody = []

    # Scale volumes by section energy
    melody_vol = int(54 * section_energy)
    harmony_vol = int(40 * section_energy)
    arp_vol = int(36 * section_energy)

    # ── Melody ──
    if layers["melody"]:
        melody = _generate_melody(
            scale_notes, chord_notes, ROWS_PER_PATTERN, section_density,
            motif=section_motif, is_answer=is_answer, phrased=use_phrased,
        )
        _apply_notes_to_pattern(
            pat, CH_MELODY, melody, melody_sample,
            volume=melody_vol, humanize=True,
        )
        _apply_vibrato(pat, CH_MELODY, melody,
                       speed=vibrato_speed, depth=vibrato_depth)

    # ── Harmony ──
    if layers["harmony"]:
        tremolo_val = ((3 & 0x0F) << 4) | (2 & 0x0F)
        harmony_channels = [CH_HARMONY, CH_HARMONY2, CH_HARMONY3]

        if melody and sec_type in ("chorus", "bridge") and random.random() < 0.3:
            counter = _generate_counter_melody(
                scale_notes, chord_notes, melody, ROWS_PER_PATTERN)
            _apply_notes_to_pattern(
                pat, CH_HARMONY, counter, sample_map["harmony"],
                volume=int(36 * section_energy), humanize=True,
            )
            voices = _generate_harmony(
                chord_notes, ROWS_PER_PATTERN,
                voicing=voicing_style,
                num_voices=min(2, num_harmony_voices),
            )
            for v_idx, voice_notes in enumerate(voices):
                if v_idx + 1 < len(harmony_channels):
                    _apply_notes_to_pattern(
                        pat, harmony_channels[v_idx + 1], voice_notes,
                        sample_map["harmony"],
                        volume=_humanize_volume(int(34 * section_energy), 4),
                        effect=FX_TREMOLO, effect_val=tremolo_val,
                        humanize=True,
                    )
        else:
            voices = _generate_harmony(
                chord_notes, ROWS_PER_PATTERN,
                voicing=voicing_style,
                num_voices=num_harmony_voices,
            )
            for v_idx, voice_notes in enumerate(voices):
                if v_idx < len(harmony_channels):
                    vol = harmony_vol if v_idx == 0 else int(34 * section_energy)
                    _apply_notes_to_pattern(
                        pat, harmony_channels[v_idx], voice_notes,
                        sample_map["harmony"],
                        volume=_humanize_volume(vol, 4),
                        effect=FX_TREMOLO, effect_val=tremolo_val,
                        humanize=True,
                    )

    # ── Bass ──
    if layers["bass"]:
        bass = _generate_bass(chord_root, chord_type, ROWS_PER_PATTERN, section_bass,
                              weight=bass_weight)
        bass_vol = {"heavy": 255, "medium": 150, "light": 100}.get(bass_weight, 255)
        if use_bass_porta and len(bass) > 1:
            _apply_portamento(
                pat, CH_BASS, bass, sample_map["bass"],
                volume=bass_vol, porta_speed=porta_speed, humanize=False,
            )
        else:
            _apply_notes_to_pattern(
                pat, CH_BASS, bass, sample_map["bass"],
                volume=bass_vol if bass_vol < 255 else 255,
                humanize=True,
            )
        if bass_weight in ("light", "medium"):
            cut_after = 2 if bass_weight == "light" else 4
            for row, _ in bass:
                cut_row = row + cut_after
                if cut_row < ROWS_PER_PATTERN:
                    if pat.data[cut_row][CH_BASS].note == 0:
                        pat.data[cut_row][CH_BASS] = ITNote(note=NOTE_CUT)

    # ── Arpeggio ──
    if layers["arp"]:
        arp = _generate_arpeggio(chord_notes, ROWS_PER_PATTERN, arp_style)
        _apply_notes_to_pattern(
            pat, CH_ARP, arp, sample_map["arp"],
            volume=arp_vol, humanize=True,
        )

    # ── Drums ──
    if layers["drums"]:
        section_drum = theory.random_drum_pattern_for_section(
            sec_type, drum_pattern, drum_density)
        drum_hits = _generate_drums(section_drum, ROWS_PER_PATTERN)

        is_last_chord = chord_idx == len(section_prog) - 1
        if fill_pattern and is_last_chord and not is_ending:
            fill_hits = _generate_drums(fill_pattern, ROWS_PER_PATTERN)
            half = ROWS_PER_PATTERN // 2
            for drum_name, hits in fill_hits.items():
                fill_rows = [h for h in hits if h >= half]
                if fill_rows:
                    if drum_name not in drum_hits:
                        drum_hits[drum_name] = []
                    drum_hits[drum_name] = [h for h in drum_hits.get(drum_name, []) if h < half]
                    drum_hits[drum_name].extend(fill_rows)
            if "crash" not in drum_hits:
                drum_hits["crash"] = []

        _apply_drums_to_pattern(pat, drum_hits, sample_map, swing=swing_amount)

        for r in range(pat.rows):
            note = pat.data[r][CH_HIHAT]
            if note.note != 0:
                note.volume = _humanize_volume(38, 8)

        if chord_idx == 0 and sec_type in ("chorus", "bridge"):
            crash_inst = sample_map.get("crash")
            if crash_inst:
                pat.data[0][CH_CRASH] = ITNote(
                    note=midi_to_it_note(60),
                    instrument=crash_inst,
                    volume=int(52 * section_energy),
                )

    # ── Section transitions ──
    if is_intro and chord_idx == 0:
        for ch in [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP]:
            _apply_fade(pat, ch, fade_in=True, rows_count=16)

    if is_ending and chord_idx == len(section_prog) - 1:
        if ending_style in ("fadeout", "tag"):
            for ch in range(NUM_CHANNELS):
                _apply_fade(pat, ch, fade_out=True, rows_count=24)

    return pat


def compose_song(seed: int | None = None, tempo_pref: str = "random",
                  energy_pref: str = "random", scale_pref: str = "random",
                  style_pref: str = "random", drum_density: str = "normal",
                  drum_fills: bool = True, drum_swing: str = "off",
                  melody_style: str = "phrased",
                  harmony_voicing: str = "full",
                  harmony_mode: str = "sustain",
                  bass_weight: str = "heavy",
                  song_form: str = "random") -> dict:
    """Compose a complete procedural song. Returns a dict for write_it_file."""
    if seed is not None:
        random.seed(seed)

    # ── Musical choices ──
    key = theory.random_key()

    if scale_pref == "minor":
        scale_name = random.choice(["natural_minor", "harmonic_minor", "dorian", "phrygian"])
    elif scale_pref == "major":
        scale_name = random.choice(["major", "mixolydian"])
    elif scale_pref == "pentatonic":
        scale_name = random.choice(["minor_pentatonic", "major_pentatonic"])
    else:
        scale_name = theory.random_scale()

    progression = theory.random_progression(scale_name)
    drum_pattern = theory.random_drum_pattern()

    if tempo_pref == "slow":
        tempo = random.randint(80, 110)
    elif tempo_pref == "medium":
        tempo = random.randint(110, 140)
    elif tempo_pref == "fast":
        tempo = random.randint(140, 180)
    else:
        tempo = theory.random_tempo()

    scale_notes = theory.build_scale(key, scale_name, octaves=4)
    speed = random.choice([4, 5, 6])

    # ── Instruments ──
    if style_pref == "genesis":
        instruments = _pick_instruments(prefer_fm=True, bass_weight=bass_weight)
    elif style_pref == "snes":
        instruments = _pick_instruments(prefer_fm=False, bass_weight=bass_weight)
    else:
        instruments = _pick_instruments(bass_weight=bass_weight)
    samples, sample_map = _build_samples(instruments)

    # ── Energy / style ──
    if energy_pref == "chill":
        bass_style = random.choice(["steady", "steady", "walking"])
        arp_style = random.choice(["up", "down", "updown"])
        melody_density = random.uniform(0.25, 0.40)
    elif energy_pref == "intense":
        bass_style = random.choice(["driving", "driving", "octave"])
        arp_style = random.choice(["updown", "random", "up"])
        melody_density = random.uniform(0.55, 0.75)
    else:
        bass_style = random.choice(["steady", "octave", "walking", "driving"])
        arp_style = random.choice(["up", "down", "updown", "random"])
        melody_density = random.uniform(0.35, 0.65)

    # ── Song structure (from structure module) ──
    song_structure, section_layers_map, energy_curve, ending_style, form_name = struct.generate_structure(form=song_form)

    # ── Motifs ──
    use_phrased = melody_style == "phrased"
    if use_phrased:
        chorus_motif = _generate_motif(length=random.choice([4, 5]))
        verse_motif = _vary_motif(chorus_motif, 0.4)
        bridge_motif = _generate_motif(length=random.choice([3, 4]))
    else:
        chorus_motif = verse_motif = bridge_motif = None

    # ── Harmony config ──
    num_harmony_voices = 3 if harmony_voicing == "full" else 1
    voicing_style = harmony_mode

    # ── Progression variation ──
    alt_progression = theory.random_alternate_progression(scale_name, progression)
    use_alt_chorus = random.random() < 0.5
    modulate_chorus = random.random() < 0.25
    modulation_semitones = 1 if modulate_chorus else 0

    # ── Effects ──
    vibrato_speed = random.choice([3, 4, 5])
    vibrato_depth = random.choice([2, 3, 4])
    porta_speed = random.choice([16, 24, 32, 48])
    use_bass_porta = bass_style in ("walking", "steady")
    swing_amount = {"off": 0, "light": 1, "heavy": 2}.get(drum_swing, 0)
    fill_pattern = theory.random_drum_fill() if drum_fills else None

    # ── Instrument swaps ──
    alt_lead = random.choice([n for n in (
        ["square_lead", "pulse_lead", "saw_lead", "fm_lead", "fm_bell", "triangle_lead"]
    ) if n != instruments["melody"]])
    alt_lead_sample_idx = None

    # ── Generate patterns ──
    patterns = []
    pattern_cache = {}

    for section in song_structure:
        layers = section_layers_map.get(section, section_layers_map.get("verse1"))
        sec_type = struct.section_type(section)
        is_intro = section == "intro"
        is_ending = section in ("outro", "tag")
        section_energy = energy_curve.get(section, 0.7)

        section_density = melody_density * section_energy
        if is_ending:
            section_density = max(section_density, 0.45)

        section_prog = struct.get_section_progression(
            section, progression, alt_progression, use_alt_chorus)
        section_bass = _pick_section_bass(bass_weight, section_energy, bass_style)

        for chord_idx, (degree, chord_type) in enumerate(section_prog):
            cache_key = (section, chord_idx)
            if cache_key in pattern_cache:
                continue

            chord_root = key + (scale_notes[degree] - scale_notes[0]) if degree < len(scale_notes) else key
            if modulate_chorus and sec_type == "chorus":
                chord_root += modulation_semitones
            chord_notes = theory.build_chord(chord_root, chord_type)

            # Instrument swap for verse2/chorus3
            melody_sample = sample_map["melody"]
            if section in ("verse2", "chorus3"):
                if alt_lead_sample_idx is None:
                    data, length, vol = smp.generate_instrument(alt_lead)
                    it_sample = ITSample(
                        name=alt_lead.replace("_", " ").title(),
                        filename=alt_lead[:12],
                        data=data, length=length,
                        loop=True, loop_start=0, loop_end=length,
                        default_volume=vol, c5_speed=smp.SAMPLE_RATE,
                    )
                    samples.append(it_sample)
                    alt_lead_sample_idx = len(samples)
                melody_sample = alt_lead_sample_idx

            section_motif = _pick_section_motif(
                sec_type, use_phrased, chorus_motif, verse_motif, bridge_motif)

            pat = _compose_pattern(
                scale_notes=scale_notes, chord_root=chord_root,
                chord_type=chord_type, chord_notes=chord_notes,
                layers=layers, sec_type=sec_type, section=section,
                section_energy=section_energy, section_density=section_density,
                section_bass=section_bass, sample_map=sample_map, samples=samples,
                melody_sample=melody_sample, use_phrased=use_phrased,
                section_motif=section_motif, chord_idx=chord_idx,
                is_answer=(chord_idx % 2 == 1),
                voicing_style=voicing_style, num_harmony_voices=num_harmony_voices,
                vibrato_speed=vibrato_speed, vibrato_depth=vibrato_depth,
                bass_weight=bass_weight, use_bass_porta=use_bass_porta,
                porta_speed=porta_speed, arp_style=arp_style,
                drum_pattern=drum_pattern, drum_density=drum_density,
                fill_pattern=fill_pattern, section_prog=section_prog,
                is_ending=is_ending, ending_style=ending_style,
                swing_amount=swing_amount, is_intro=is_intro,
            )

            pattern_cache[cache_key] = len(patterns)
            patterns.append(pat)

    # ── Build orders ──
    orders = struct.build_orders(
        song_structure, pattern_cache, progression, alt_progression, use_alt_chorus)

    # ── Song info ──
    key_name = theory.NOTE_NAMES[key % 12]
    song_name = f"BitComposer - {key_name} {scale_name.replace('_', ' ').title()}"
    display_structure = [struct.section_type(s) for s in song_structure]

    info = {
        "key": key_name,
        "scale": scale_name,
        "tempo": tempo,
        "speed": speed,
        "bass_style": bass_style,
        "bass_weight": bass_weight,
        "arp_style": arp_style,
        "melody_density": round(melody_density, 2),
        "melody_style": melody_style,
        "melody_contour": chorus_motif["contour_name"] if use_phrased and chorus_motif else "n/a",
        "harmony_voicing": harmony_voicing,
        "harmony_mode": harmony_mode,
        "chorus_modulated": modulate_chorus,
        "chorus_alt_prog": use_alt_chorus,
        "ending_style": ending_style,
        "song_form": form_name,
        "alt_lead": alt_lead if alt_lead_sample_idx else None,
        "instruments": instruments,
        "progression": [(d, t) for d, t in progression],
        "structure": display_structure,
        "num_patterns": len(patterns),
        "num_orders": len(orders),
    }

    return {
        "name": song_name[:25],
        "key": key,
        "scale": scale_name,
        "tempo": tempo,
        "speed": speed,
        "samples": samples,
        "patterns": patterns,
        "orders": orders,
        "info": info,
    }


def compose_and_save(filepath: str, seed: int | None = None,
                     tempo: str = "random", energy: str = "random",
                     scale: str = "random", style: str = "random",
                     drum_density: str = "normal", drum_fills: bool = True,
                     drum_swing: str = "off",
                     melody_style: str = "phrased",
                     harmony_voicing: str = "full",
                     harmony_mode: str = "sustain",
                     bass_weight: str = "heavy",
                     song_form: str = "random") -> dict:
    """Compose a song and save it as an IT file. Returns song info."""
    song = compose_song(seed=seed, tempo_pref=tempo, energy_pref=energy,
                        scale_pref=scale, style_pref=style,
                        drum_density=drum_density, drum_fills=drum_fills,
                        drum_swing=drum_swing, melody_style=melody_style,
                        harmony_voicing=harmony_voicing,
                        harmony_mode=harmony_mode,
                        bass_weight=bass_weight,
                        song_form=song_form)
    write_it_file(
        filepath=filepath,
        song_name=song["name"],
        samples=song["samples"],
        patterns=song["patterns"],
        orders=song["orders"],
        tempo=song["tempo"],
        speed=song["speed"],
        num_channels=NUM_CHANNELS,
    )
    return song["info"]
