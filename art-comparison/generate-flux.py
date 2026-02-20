#!/usr/bin/env python3
"""Generate art comparison images using Hugging Face's FLUX.1-schnell model."""

import os
import sys
from pathlib import Path

import requests

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("HF_TOKEN="):
                HF_TOKEN = line.split("=", 1)[1].strip()
                break

if not HF_TOKEN:
    print("Error: HF_TOKEN not found")
    sys.exit(1)

API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
OUTPUT_DIR = Path(__file__).parent / "flux"

PROMPTS = {
    "01-op-art": (
        "Op art black and white optical illusion, concentric circles creating 3D sphere bulge effect, "
        "Victor Vasarely style, high contrast, geometric precision, hypnotic pattern"
    ),
    "02-japanese-landscape": (
        "Minimalist Japanese landscape, single cherry blossom tree on gentle hill, "
        "soft pink and grey palette, negative space, ukiyo-e influenced, serene atmosphere, "
        "distant misty mountains, falling petals, contemplative mood"
    ),
    "03-retro-poster": (
        "Vintage 1960s Swiss International Style jazz festival poster, bold Helvetica typography, "
        "geometric shapes, limited color palette of deep orange red cream and charcoal, "
        "abstract saxophone player silhouette, Zurich 1965, Bauhaus influenced grid layout"
    ),
    "04-abstract-expressionist": (
        "Abstract expressionist painting, bold dramatic brush strokes in deep blue and gold amber, "
        "Franz Kline inspired black gestures, Rothko color field areas, emotional intensity, "
        "paint splatter and drips, layered textures, large canvas feel"
    ),
    "05-isometric-coffee-shop": (
        "Isometric illustration of a cozy coffee shop interior, flat design style, "
        "warm pastel colors, espresso machine on wooden counter, small tables with chairs, "
        "pendant lighting, potted plants, shelves with coffee jars, warm and inviting atmosphere"
    ),
    "06-pixel-art-cyberpunk": (
        "16-bit pixel art cyberpunk city street at night, neon signs in Japanese katakana, "
        "hot pink and cyan neon glow, wet street with reflections in puddles, rain, "
        "dark building silhouettes, retro SNES game aesthetic, atmospheric lighting"
    ),
    "07-botanical-butterfly": (
        "Hyperdetailed watercolor botanical illustration, monarch butterfly perched on purple coneflower echinacea, "
        "scientific accuracy, delicate wing veins and patterns, soft natural light, "
        "warm cream paper background, Danaus plexippus, botanical art style"
    ),
    "08-fractal-mandelbrot": (
        "Mandelbrot fractal zoom into Seahorse Valley, vibrant rainbow gradient coloring, "
        "deep purple blue cyan green gold orange red palette, mathematical beauty, "
        "cosmic colors, high detail spiraling tendrils, smooth color transitions, dark interior"
    ),
}


def generate_image(prompt: str, output_path: Path) -> bool:
    """Call HF inference API and save the resulting image."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    try:
        print(f"  Generating... ", end="", flush=True)
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": prompt},
            timeout=120,
        )
        response.raise_for_status()

        if response.headers.get("content-type", "").startswith("image/"):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            size_kb = len(response.content) / 1024
            print(f"OK ({size_kb:.0f} KB)")
            return True
        else:
            print(f"Unexpected response: {response.text[:200]}")
            return False
    except requests.exceptions.HTTPError as e:
        print(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate art comparison images with FLUX.1-schnell")
    parser.add_argument("names", nargs="*", help="Image names from PROMPTS registry (e.g. 01-op-art)")
    args = parser.parse_args()

    targets = args.names if args.names else list(PROMPTS.keys())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(targets)} image(s) with FLUX.1-schnell\n")

    results = {"success": [], "failed": []}

    for name in targets:
        if name not in PROMPTS:
            print(f"[SKIP] Unknown: {name}")
            continue

        output_path = OUTPUT_DIR / f"{name}.png"
        print(f"[{name}]")
        print(f"  Prompt: {PROMPTS[name][:80]}...")

        if generate_image(PROMPTS[name], output_path):
            results["success"].append(name)
            print(f"  Saved: {output_path}")
        else:
            results["failed"].append(name)

        print()

    print(f"\nDone: {len(results['success'])} success, {len(results['failed'])} failed")
    if results["failed"]:
        print(f"Failed: {', '.join(results['failed'])}")

    # Print prompts summary for Gemini
    print("\n" + "=" * 60)
    print("PROMPTS FOR GEMINI (copy-paste):")
    print("=" * 60)
    for name, prompt in PROMPTS.items():
        if name in targets:
            print(f"\n--- {name} ---")
            print(prompt)


if __name__ == "__main__":
    main()
