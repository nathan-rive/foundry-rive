#!/usr/bin/env python3
"""Render labelled contact sheets of token states.

usage: python3 tools/sheet.py OUT.png "label|--data=a=1 --data=b=2" ...
Each cell is rendered at 512px and shown at 160px and 56px (token-size check).
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def render(args, path, advance="60"):
    cmd = ["rive", ROOT, f"--screenshot={path}", f"--advance={advance}"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(path):
        print(r.stdout[-800:], r.stderr[-800:])
        raise SystemExit(f"render failed: {args}")


def main():
    out = sys.argv[1]
    cells = sys.argv[2:]
    tmp = tempfile.mkdtemp()
    big, small, pad, lab = 170, 56, 10, 18
    cols = min(len(cells), 6)
    rows = (len(cells) + cols - 1) // cols
    cw = big + pad
    ch = big + small + lab + pad * 2
    sheet = Image.new("RGB", (cols * cw + pad, rows * ch + pad), (236, 233, 226))
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(cells):
        label, _, a = c.partition("|")
        adv = "60"
        args = []
        for tok in a.split():
            if tok.startswith("--advance="):
                adv = tok.split("=", 1)[1]
            else:
                args.append(tok)
        p = os.path.join(tmp, f"{i}.png")
        render(args, p, adv)
        im = Image.open(p).convert("RGBA")
        x = pad + (i % cols) * cw
        y = pad + (i // cols) * ch
        sheet.paste(im.resize((big, big), Image.LANCZOS), (x, y), im.resize((big, big), Image.LANCZOS))
        sm = im.resize((small, small), Image.LANCZOS)
        sheet.paste(sm, (x, y + big + 4), sm)
        d.text((x + small + 6, y + big + 8), label, fill=(30, 30, 30))
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
