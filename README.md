# bitcomposer

Procedural 16-bit chiptune music generator. Creates Impulse Tracker (.it) module files using algorithmically composed melodies, bass lines, arpeggios, harmony, and drum patterns.

The generated music is inspired by the SNES and Sega Genesis era — FM synthesis bells, square wave leads, driving bass lines, and classic tracker drum sounds.

## Features

- **Motif-based melody** — phrase structure with contour shaping (arch, climb, valley, etc.), question-answer phrasing, and chorus callbacks so the hook comes back
- **Full harmony** — 2-3 note chord voicings across 3 channels, counter-melody generation, sustain/stabs/rhythmic modes
- **Dynamic arrangement** — energy curves across sections, gradual texture build, variable structure (tag/abrupt/fadeout endings, double bridges), instrument swaps between sections
- **Extended synthesis** — 30+ instrument presets: classic waveforms (square, saw, triangle), multi-operator FM (organ, brass, pad), PWM sweep, supersaw, filtered/distorted bass, layered drums with reverb tails
- **IT effects** — vibrato, portamento, tremolo, volume slides, velocity humanization
- **Drum system** — 6 drum channels, per-section pattern selection, fill patterns at transitions, swing/shuffle, sparse/busy density variants
- **Music theory** — 8 scales, 20+ chord progressions, 7 chord types, progression variation between sections, key modulation (chorus up a semitone)
- **12-channel output** — melody, 3 harmony, bass, arp, kick, snare, hihat, tom, crash, open hihat
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

# Generate with verbose output
bitcomposer -v -o mysong.it

# Generate 5 songs into a directory
bitcomposer -n 5 -d ~/Music/Chiptune/

# Reproducible with a seed
bitcomposer -s 42 -o seed42.it
```

### Style Options

```bash
# Composition
--tempo slow|medium|fast|random
--energy chill|normal|intense|random
--scale minor|major|pentatonic|random
--style snes|genesis|random

# Drums
--drum-density sparse|normal|busy
--no-fills
--swing off|light|heavy

# Melody
--melody simple|phrased

# Harmony
--harmony-voicing thin|full
--harmony-mode stabs|sustain|rhythmic
```

### Example Presets

```bash
# Genesis boss fight
bitcomposer -v -o boss.it --tempo fast --energy intense --style genesis --drum-density busy --swing heavy --harmony-mode rhythmic

# Chill exploration
bitcomposer -v -o chill.it --tempo slow --energy chill --scale pentatonic --style snes --drum-density sparse --no-fills --swing light

# Dark dungeon
bitcomposer -v -o dungeon.it --tempo slow --energy chill --scale minor --drum-density sparse --no-fills --harmony-voicing thin --harmony-mode stabs

# Credits roll
bitcomposer -v -o credits.it --tempo slow --energy chill --scale major --style snes --drum-density sparse --no-fills
```

## How It Works

1. **Pick a key and scale** — randomly selects from game-music-friendly scales (minor pentatonic, dorian, harmonic minor, etc.)
2. **Choose chord progressions** — selects progressions for verse and chorus (50% chance of different chorus chords), with optional key modulation
3. **Generate motifs** — creates rhythmic+melodic templates with contour shapes that repeat and vary across sections, giving the melody recognizable phrases
4. **Select instruments** — picks from 30+ synthesized presets based on style preference (SNES waveforms vs Genesis FM), with alternate lead for later sections
5. **Compose layers**:
   - **Melody** — motif-based phrases with question-answer structure, vibrato, register variation
   - **Harmony** — 2-3 note chord voicings with tremolo, optional counter-melody in chorus/bridge
   - **Bass** — root movement adapting style to section energy (steady → driving)
   - **Arpeggio** — chord tones in patterns (up, down, up-down, random)
   - **Drums** — per-section patterns with fills at transitions, swing on hi-hats, crash on downbeats
6. **Arrange** — energy curves scale volumes and density across sections (intro 50% → final chorus 100%), variable structure with multiple ending styles
7. **Write** — outputs a valid 12-channel Impulse Tracker module file

## License

MIT
