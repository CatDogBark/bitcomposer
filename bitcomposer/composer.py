"""
Procedural song composer.

Generates complete songs by combining music theory, instrument samples,
and pattern generation into playable Impulse Tracker modules.
"""

import random

from . import theory
from . import samples as smp
from .it_format import (
    ITSample, ITPattern, ITNote, midi_to_it_note, NOTE_CUT, NOTE_OFF,
    write_it_file,
)


# Channel assignments
CH_MELODY = 0
CH_HARMONY = 1
CH_BASS = 2
CH_ARP = 3
CH_KICK = 4
CH_SNARE = 5
CH_HIHAT = 6
CH_EXTRA = 7

NUM_CHANNELS = 8
ROWS_PER_PATTERN = 64
STEPS_PER_ROW = 4  # 16 steps = 64 rows / 4 rows per step


def _pick_instruments() -> dict[str, str]:
    """Pick a random instrument set for the song."""
    lead_choices = ["square_lead", "pulse_lead", "saw_lead", "fm_lead", "fm_bell"]
    harmony_choices = ["triangle_lead", "square_lead", "fm_bell", "pulse_lead"]
    bass_choices = ["saw_bass", "triangle_bass", "fm_bass", "sine_bass", "square_bass"]
    arp_choices = ["square_lead", "pulse_lead", "fm_bell", "triangle_lead"]

    lead = random.choice(lead_choices)
    harmony = random.choice([h for h in harmony_choices if h != lead] or harmony_choices)
    bass = random.choice(bass_choices)
    arp = random.choice([a for a in arp_choices if a != lead] or arp_choices)

    return {
        "melody": lead,
        "harmony": harmony,
        "bass": bass,
        "arp": arp,
        "kick": "kick",
        "snare": "snare",
        "hihat": "hihat",
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
        is_drum = key in ("kick", "snare", "hihat")

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


def _generate_melody(scale_notes: list[int], chord_notes: list[int],
                     rows: int, density: float = 0.5) -> list[tuple[int, int]]:
    """Generate a melody line. Returns [(row, midi_note), ...]."""
    notes = []
    # Melody range: octave 4-5 (MIDI 60-83)
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return notes

    # Start near a chord tone
    chord_in_range = [n for n in chord_notes if n in melody_notes]
    current = random.choice(chord_in_range) if chord_in_range else random.choice(melody_notes)

    row = 0
    while row < rows:
        if random.random() < density:
            # Step movement: prefer small intervals
            idx = melody_notes.index(current) if current in melody_notes else 0
            step = random.choices([-2, -1, 0, 1, 2], weights=[10, 25, 15, 25, 10], k=1)[0]
            new_idx = max(0, min(len(melody_notes) - 1, idx + step))
            current = melody_notes[new_idx]

            # Occasional jump to chord tone
            if random.random() < 0.2 and chord_in_range:
                current = random.choice(chord_in_range)

            # Note duration: 2-8 rows
            duration = random.choice([2, 4, 4, 4, 8])
            notes.append((row, current))
            row += duration
        else:
            row += random.choice([2, 4])

    return notes


def _generate_bass(root: int, chord_type: str,
                   rows: int, style: str = "steady") -> list[tuple[int, int]]:
    """Generate a bass line. Returns [(row, midi_note), ...]."""
    # Bass in octave 2-3 (MIDI 36-59)
    bass_root = root
    while bass_root >= 48:
        bass_root -= 12
    while bass_root < 36:
        bass_root += 12

    chord = theory.build_chord(bass_root, chord_type)
    notes = []

    if style == "steady":
        # Play root on beats
        for row in range(0, rows, 8):
            notes.append((row, bass_root))
    elif style == "octave":
        # Alternate root and octave
        for i, row in enumerate(range(0, rows, 4)):
            if i % 2 == 0:
                notes.append((row, bass_root))
            else:
                notes.append((row, bass_root + 12))
    elif style == "walking":
        # Walk through chord tones
        for i, row in enumerate(range(0, rows, 4)):
            note = chord[i % len(chord)]
            notes.append((row, note))
    elif style == "driving":
        # Eighth note root
        for row in range(0, rows, 2):
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


def _apply_notes_to_pattern(pattern: ITPattern, channel: int,
                            note_list: list[tuple[int, int]],
                            instrument: int, volume: int = 255):
    """Write note events into a pattern channel."""
    for row, midi_note in note_list:
        if 0 <= row < pattern.rows:
            it_note = midi_to_it_note(midi_note)
            pattern.data[row][channel] = ITNote(
                note=it_note,
                instrument=instrument,
                volume=volume,
            )


def _apply_drums_to_pattern(pattern: ITPattern, drum_hits: dict[str, list[int]],
                            sample_map: dict[str, int]):
    """Write drum hits into pattern."""
    drum_channels = {"kick": CH_KICK, "snare": CH_SNARE, "hihat": CH_HIHAT}
    # Drum notes: play at C-5 (MIDI 60 -> IT note 48)
    drum_note = midi_to_it_note(60)

    for drum, hits in drum_hits.items():
        ch = drum_channels.get(drum)
        inst = sample_map.get(drum)
        if ch is None or inst is None:
            continue
        for row in hits:
            if 0 <= row < pattern.rows:
                pattern.data[row][ch] = ITNote(
                    note=drum_note,
                    instrument=inst,
                )


def compose_song(seed: int | None = None) -> dict:
    """
    Compose a complete procedural song.

    Returns a dict with all the info needed to write the IT file:
    {
        "name": str,
        "key": int,
        "scale": str,
        "tempo": int,
        "samples": [ITSample, ...],
        "patterns": [ITPattern, ...],
        "orders": [int, ...],
        "info": {...},  # Metadata about choices made
    }
    """
    if seed is not None:
        random.seed(seed)

    # Musical choices
    key = theory.random_key()
    scale_name = theory.random_scale()
    progression = theory.random_progression(scale_name)
    drum_pattern = theory.random_drum_pattern()
    tempo = theory.random_tempo()

    # Build scale notes across a few octaves
    scale_notes = theory.build_scale(key, scale_name, octaves=4)

    # Speed: rows per tick. 6 is standard, 4 is faster feel.
    speed = random.choice([4, 5, 6])

    # Pick instruments and build samples
    instruments = _pick_instruments()
    samples, sample_map = _build_samples(instruments)

    # Composition styles
    bass_style = random.choice(["steady", "octave", "walking", "driving"])
    arp_style = random.choice(["up", "down", "updown", "random"])
    melody_density = random.uniform(0.35, 0.65)

    # Determine which layers appear in which sections
    # Song structure: intro, verse, chorus, verse, chorus, bridge, chorus, outro
    section_layers = {
        "intro":  {"drums": False, "bass": True,  "melody": False, "arp": True,  "harmony": False},
        "verse":  {"drums": True,  "bass": True,  "melody": True,  "arp": False, "harmony": False},
        "chorus": {"drums": True,  "bass": True,  "melody": True,  "arp": True,  "harmony": True},
        "bridge": {"drums": True,  "bass": True,  "melody": False, "arp": True,  "harmony": False},
        "outro":  {"drums": False, "bass": True,  "melody": True,  "arp": False, "harmony": False},
    }

    song_structure = ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"]

    patterns = []
    pattern_cache = {}  # (section, chord_idx) -> pattern_index

    for section in song_structure:
        layers = section_layers[section]

        for chord_idx, (degree, chord_type) in enumerate(progression):
            cache_key = (section, chord_idx)
            if cache_key in pattern_cache:
                continue  # Already generated

            chord_root = key + (scale_notes[degree] - scale_notes[0]) if degree < len(scale_notes) else key
            chord_notes = theory.build_chord(chord_root, chord_type)

            pat = ITPattern(rows=ROWS_PER_PATTERN, channels=NUM_CHANNELS)

            # Melody
            if layers["melody"]:
                melody = _generate_melody(scale_notes, chord_notes, ROWS_PER_PATTERN, melody_density)
                _apply_notes_to_pattern(pat, CH_MELODY, melody, sample_map["melody"])

            # Harmony (melody transposed or chord stabs)
            if layers["harmony"]:
                # Chord stabs on beats
                stab_rows = list(range(0, ROWS_PER_PATTERN, 16))
                for row in stab_rows:
                    for i, cn in enumerate(chord_notes[:3]):
                        # Stack chord notes in harmony channel using volume column
                        if i == 0:
                            harmony_note = cn
                            while harmony_note < 60:
                                harmony_note += 12
                            while harmony_note > 84:
                                harmony_note -= 12
                            pat.data[row][CH_HARMONY] = ITNote(
                                note=midi_to_it_note(harmony_note),
                                instrument=sample_map["harmony"],
                                volume=40,
                            )

            # Bass
            if layers["bass"]:
                bass = _generate_bass(chord_root, chord_type, ROWS_PER_PATTERN, bass_style)
                _apply_notes_to_pattern(pat, CH_BASS, bass, sample_map["bass"])

            # Arpeggio
            if layers["arp"]:
                arp = _generate_arpeggio(chord_notes, ROWS_PER_PATTERN, arp_style)
                _apply_notes_to_pattern(pat, CH_ARP, arp, sample_map["arp"], volume=36)

            # Drums
            if layers["drums"]:
                drum_hits = _generate_drums(drum_pattern, ROWS_PER_PATTERN)
                _apply_drums_to_pattern(pat, drum_hits, sample_map)

            pattern_cache[cache_key] = len(patterns)
            patterns.append(pat)

    # Build order list from song structure
    orders = []
    for section in song_structure:
        for chord_idx in range(len(progression)):
            cache_key = (section, chord_idx)
            orders.append(pattern_cache[cache_key])

    # Song name
    key_name = theory.NOTE_NAMES[key % 12]
    song_name = f"BitComposer - {key_name} {scale_name.replace('_', ' ').title()}"

    info = {
        "key": key_name,
        "scale": scale_name,
        "tempo": tempo,
        "speed": speed,
        "bass_style": bass_style,
        "arp_style": arp_style,
        "melody_density": round(melody_density, 2),
        "instruments": instruments,
        "progression": [(d, t) for d, t in progression],
        "structure": song_structure,
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


def compose_and_save(filepath: str, seed: int | None = None) -> dict:
    """Compose a song and save it as an IT file. Returns song info."""
    song = compose_song(seed=seed)
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
