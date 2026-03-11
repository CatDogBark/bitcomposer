"""
Bass and arpeggio generation.
"""

import random

from . import theory


def generate_bass(root: int, chord_type: str,
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


def generate_arpeggio(chord_notes: list[int], rows: int,
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


def pick_section_bass(bass_weight: str, section_energy: float,
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
