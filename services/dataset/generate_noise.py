#!/usr/bin/env python3
"""
generate_noise.py — Generate noisy/corrupted document variants for robustness testing.

Applies random OCR-like noise: character substitution, line deletion, random insertions.

Usage:
  python generate_noise.py --input ./samples/invoices --output ./samples/noisy --noise 0.05
"""
import argparse
import random
import string
from pathlib import Path


def add_character_noise(text: str, rate: float) -> str:
    """Randomly substitute, delete, or insert characters."""
    result: list[str] = []
    for ch in text:
        roll = random.random()
        if roll < rate * 0.4:
            # substitute with a visually similar char
            similar = {
                'o': '0', '0': 'o', 'i': '1', '1': 'i', 'l': '1',
                'S': '5', '5': 'S', 'B': '8', '8': 'B', 'G': '6',
            }
            result.append(similar.get(ch, random.choice(string.ascii_letters)))
        elif roll < rate * 0.7:
            pass  # delete character
        elif roll < rate:
            result.append(ch)
            result.append(random.choice(string.ascii_lowercase))  # insert extra char
        else:
            result.append(ch)
    return ''.join(result)


def add_line_noise(text: str, delete_rate: float) -> str:
    """Randomly delete lines (simulates OCR missing a line)."""
    lines = text.split('\n')
    kept = [line for line in lines if random.random() > delete_rate]
    return '\n'.join(kept)


def add_whitespace_noise(text: str) -> str:
    """Add random extra spaces and newlines."""
    lines = text.split('\n')
    result = []
    for line in lines:
        if random.random() < 0.1:
            result.append('')  # blank line insertion
        result.append(line + ' ' * random.randint(0, 5))
    return '\n'.join(result)


def noisify(text: str, noise_rate: float) -> str:
    text = add_line_noise(text, delete_rate=noise_rate * 0.3)
    text = add_character_noise(text, rate=noise_rate)
    text = add_whitespace_noise(text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Add OCR noise to document text files")
    parser.add_argument("--input", type=str, required=True, help="Input directory with .txt files")
    parser.add_argument("--output", type=str, required=True, help="Output directory for noisy files")
    parser.add_argument("--noise", type=float, default=0.05, help="Noise rate 0.0–1.0 (default: 0.05)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = list(input_dir.glob("*.txt"))
    if not files:
        print(f"No .txt files found in {input_dir}")
        return

    for src in files:
        original = src.read_text(encoding="utf-8")
        noisy = noisify(original, args.noise)
        dest = output_dir / f"noisy_{src.name}"
        dest.write_text(noisy, encoding="utf-8")

    print(f"Generated {len(files)} noisy files (noise={args.noise}) in {output_dir}")


if __name__ == "__main__":
    main()
