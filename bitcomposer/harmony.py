"""
Harmony generation: chord voicings and multi-voice harmony parts.
"""

import random


HARMONY_VOICINGS = {
    "stabs": {
        "description": "Short chord stabs every 16 rows",
        "interval": 16,
        "cut_after": 6,
    },
    "sustain": {
        "description": "Sustained pad chords, held across the pattern",
        "interval": 32,
        "cut_after": 24,
    },
    "rhythmic": {
        "description": "Rhythmic chord hits synced to groove",
        "interval": 8,
        "cut_after": 4,
    },
}


def generate_harmony(chord_notes: list[int], rows: int,
                     voicing: str = "stabs",
                     num_voices: int = 2) -> list[list[tuple[int, int]]]:
    """
    Generate harmony parts for multiple channels.

    Returns a list of note lists, one per voice: [[(row, midi_note), ...], ...]
    Voice 0 = highest, Voice N = lowest (within the chord voicing range).
    Note-cut events are included as (row, -1) tuples.
    """
    # Get voicing config
    config = HARMONY_VOICINGS.get(voicing, HARMONY_VOICINGS["stabs"])
    interval = config["interval"]
    cut_after = config["cut_after"]

    # Build voiced chord notes in octave 3-4 range (MIDI 48-72)
    # One octave below melody range so harmony sits underneath
    voiced = []
    for cn in chord_notes[:4]:  # Max 4 chord tones
        note = cn
        while note < 48:
            note += 12
        while note > 72:
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

            # Add note-cut so notes don't ring indefinitely
            cut_row = actual_row + cut_after
            if cut_row < rows and cut_row < actual_row + interval:
                notes.append((cut_row, -1))  # -1 signals note-cut
        result.append(notes)

    return result
