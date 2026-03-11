"""
Command-line interface for bitcomposer.
"""

import argparse
import os
import sys
import time

from . import __version__
from .composer import compose_and_save


def main():
    parser = argparse.ArgumentParser(
        prog="bitcomposer",
        description="Procedural 16-bit chiptune music generator",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file path (default: auto-generated name in current directory)",
    )
    parser.add_argument(
        "-d", "--output-dir",
        default=".",
        help="Output directory (used when -o is not specified)",
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible output",
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=1,
        help="Number of songs to generate",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed info about generated songs",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"bitcomposer {__version__}",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    for i in range(args.count):
        seed = args.seed
        if seed is not None and args.count > 1:
            seed = seed + i

        if args.output and args.count == 1:
            filepath = args.output
        else:
            timestamp = int(time.time())
            seed_str = f"_s{seed}" if seed is not None else ""
            filepath = os.path.join(
                args.output_dir,
                f"bitcomposer_{timestamp}_{i}{seed_str}.it"
            )

        try:
            info = compose_and_save(filepath, seed=seed)
        except Exception as e:
            print(f"Error generating song: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        print(f"Generated: {filepath}")

        if args.verbose:
            print(f"  Key:         {info['key']} {info['scale']}")
            print(f"  Tempo:       {info['tempo']} BPM (speed {info['speed']})")
            print(f"  Bass:        {info['bass_style']}")
            print(f"  Arpeggio:    {info['arp_style']}")
            print(f"  Density:     {info['melody_density']}")
            print(f"  Patterns:    {info['num_patterns']}")
            print(f"  Orders:      {info['num_orders']}")
            print(f"  Instruments: {', '.join(info['instruments'].values())}")
            print(f"  Progression: {info['progression']}")
            print(f"  Structure:   {' > '.join(info['structure'])}")
            print()


if __name__ == "__main__":
    main()
