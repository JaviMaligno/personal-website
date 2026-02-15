#!/usr/bin/env python3
"""Generate blog thumbnails using Hugging Face's FLUX.1-schnell model."""

import os
import sys
import json
from pathlib import Path

import requests

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    # Try loading from .env
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
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "blog" / "generated"

PROMPTS = {
    "rlm-prototype-hero": (
        "A minimalist isometric illustration on a dark background. A glowing brain-shaped node at the center writes Python code on a floating translucent terminal. "
        "From it, five luminous threads extend outward to a grid of small document icons arranged in rows, each document briefly highlighted as the thread touches it. "
        "The threads converge back to the brain, which synthesizes the results into a single glowing summary panel. "
        'Subtle labels: "python_exec", "llm_query_batch", "final()". '
        "Style: clean tech diagram aesthetic, neon blue and amber accents on deep navy, no photorealism, no humans."
    ),
    "azure-content-filter": (
        "A minimalist isometric illustration on a dark background. A shield icon in the center with a large red X overlaid, "
        "blocking a stream of code snippets and terminal commands flowing from left to right. "
        "Some commands are highlighted in green (allowed) while others glow red (blocked). "
        "A small magnifying glass inspects individual words rather than the full context. "
        "Style: clean tech diagram aesthetic, neon blue and red accents on deep navy, no photorealism, no humans."
    ),
    "parallel-ai-agents": (
        "A minimalist isometric illustration on a dark background. Three translucent terminal windows arranged in a fan pattern, "
        "each showing different code being written simultaneously by glowing cursor points. "
        "Git branch lines connect each terminal to a central repository node at the bottom. "
        "Small progress indicators glow above each terminal. "
        "Style: clean tech diagram aesthetic, neon blue and green accents on deep navy, no photorealism, no humans."
    ),
    "claude-code-skills": (
        "A minimalist isometric illustration on a dark background. A toolbox icon in the center, open, with glowing skill cards "
        "floating out of it like a deck of cards. Each card has a small icon: a pen, a globe, a gear. "
        "Two document icons on either side labeled EN and ES are connected by dotted lines to the toolbox. "
        "Style: clean tech diagram aesthetic, neon blue and purple accents on deep navy, no photorealism, no humans."
    ),
    "mcp-server-bitbucket": (
        "A minimalist isometric illustration on a dark background. A central glowing hub node labeled MCP with "
        "radiating connection lines to surrounding icons: a git branch, a pipeline with stages, a pull request arrow, "
        "a lock icon, and a webhook bolt. Each icon floats on a small platform. "
        "Style: clean tech diagram aesthetic, neon blue and orange accents on deep navy, no photorealism, no humans."
    ),
    "typescript-agent-guardrails": (
        "A minimalist isometric illustration on a dark background. A robotic arm writing code on a floating IDE window, "
        "with TypeScript type annotations forming translucent guardrails on both sides of the code path. "
        "Red squiggly lines appear at certain points, and a small sub-agent icon swoops in to fix them. "
        "Style: clean tech diagram aesthetic, neon blue and amber accents on deep navy, no photorealism, no humans."
    ),
    "claude-coauthor-legal": (
        "A minimalist isometric illustration on a dark background. A git commit message floating in the center with "
        "'Co-Authored-By' highlighted and glowing. On one side, a gavel and scales of justice icon. "
        "On the other side, a robot silhouette and a human silhouette facing each other across a document. "
        "Question marks float subtly in the background. "
        "Style: clean tech diagram aesthetic, neon blue and gold accents on deep navy, no photorealism, no humans."
    ),
    "claude-code-agent-teams": (
        "A minimalist isometric illustration on a dark background. A tmux-style split terminal with four panes, "
        "each containing a different agent avatar (small glowing circles with role labels). "
        "Arrows flow between panes showing message passing. A lead agent node at the top coordinates the flow. "
        "Style: clean tech diagram aesthetic, neon blue and teal accents on deep navy, no photorealism, no humans."
    ),
}


def generate_image(prompt: str, output_path: Path) -> bool:
    """Call HF inference API and save the resulting image."""
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
    }

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

    parser = argparse.ArgumentParser(description="Generate blog thumbnails with FLUX.1-schnell")
    parser.add_argument("names", nargs="*", help="Article names from PROMPTS registry")
    parser.add_argument("--prompt", type=str, help="Ad-hoc prompt for a single image")
    parser.add_argument("--output", type=str, help="Output filename (e.g. 'my-article.png')")
    args = parser.parse_args()

    blog_dir = Path(__file__).parent.parent / "public" / "blog"

    # Ad-hoc mode: --prompt "..." --output "name.png"
    if args.prompt:
        if not args.output:
            print("Error: --output is required with --prompt")
            sys.exit(1)
        output_path = blog_dir / args.output
        print(f"Generating thumbnail: {args.output}")
        print(f"  Prompt: {args.prompt[:80]}...")
        if generate_image(args.prompt, output_path):
            print(f"  Saved: {output_path}")
        else:
            sys.exit(1)
        return

    # Registry mode: generate from PROMPTS dict
    targets = args.names if args.names else list(PROMPTS.keys())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(targets)} thumbnail(s) with FLUX.1-schnell\n")

    results = {"success": [], "failed": []}

    for name in targets:
        if name not in PROMPTS:
            print(f"[SKIP] Unknown article: {name}")
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


if __name__ == "__main__":
    main()
