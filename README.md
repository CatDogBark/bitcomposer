# bitcomposer

Procedural 16-bit chiptune music generator. Creates Impulse Tracker (.it) module files using algorithmically composed melodies, bass lines, arpeggios, and drum patterns.

The generated music is inspired by the SNES and Sega Genesis era — FM synthesis bells, square wave leads, driving bass lines, and classic tracker drum sounds.

## Features

- **Procedural composition** — generates complete songs with intro, verses, chorus, bridge, and outro
- **Music theory aware** — uses scales, chord progressions, and voice leading for musically coherent output
- **Synthesized instruments** — all waveforms generated from math (square, saw, triangle, FM synthesis)
- **Multiple styles** — random selection of scales (pentatonic, dorian, mixolydian, etc.), bass styles, arpeggio patterns, and drum grooves
- **Reproducible** — optional seed parameter for deterministic output
- **Standard format** — outputs .it files playable by any tracker-compatible player (libopenmpt, VLC, Audacious, OpenMPT, etc.)
- **Zero dependencies** — pure Python, no external libraries required

## Install

```bash
pip install .
```

Or run directly:

```bash
python -m bitcomposer.cli
```

## Usage

```bash
# Generate a single song
bitcomposer -o mysong.it

# Generate 5 songs into a directory
bitcomposer -n 5 -d ~/Music/Chiptune/

# Generate with a specific seed (reproducible)
bitcomposer -s 42 -o seed42.it

# Verbose output showing composition details
bitcomposer -v -o mysong.it
```

## How It Works

1. **Pick a key and scale** — randomly selects from game-music-friendly scales (minor pentatonic, dorian, harmonic minor, etc.)
2. **Choose a chord progression** — selects from common progressions appropriate for the chosen scale
3. **Select instruments** — picks from synthesized waveforms: square/pulse leads, FM bells, sawtooth bass, triangle sub, etc.
4. **Compose layers**:
   - **Melody** — step-wise motion through the scale with occasional chord-tone jumps
   - **Bass** — root movement in various styles (steady, octave, walking, driving)
   - **Arpeggio** — chord tones in patterns (up, down, up-down, random)
   - **Harmony** — chord stabs on strong beats
   - **Drums** — kick/snare/hi-hat patterns from a library of grooves
5. **Arrange** — layers are added/removed across song sections (intro → verse → chorus → bridge → outro)
6. **Write** — outputs a valid Impulse Tracker module file

## License

MIT
