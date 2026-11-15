"""Small painted touches for the title screen (Pillow): the gold-leaf
ODYSSEY and the crimson BEGIN VOYAGE banner.

Drawn at 3x and scaled down for smooth edges; cached in .art_cache/
(git-ignored) and rebuilt when VERSION changes.
"""

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

VERSION = "4"
S = 3
FONT_DIR = "/System/Library/Fonts/Supplemental"

CREAM = (240, 228, 196)
GOLD_LIGHT = (250, 226, 160)
GOLD = (214, 172, 96)
GOLD_DARK = (150, 108, 52)
CRIMSON = (152, 54, 62)           # a lighter maroon
CRIMSON_DEEP = (84, 26, 32)


def font(name, size):
    path = os.path.join(FONT_DIR, name)
    if os.path.exists(path):
        return ImageFont.truetype(path, size * S)
    return ImageFont.load_default()


def lerp(a, b, f):
    return tuple(int(x + (y - x) * f) for x, y in zip(a, b))


def spaced_mask(text, f, spacing, pad):
    """White-on-black mask of letter-spaced text, sized to fit."""
    widths = [f.getbbox(c)[2] - f.getbbox(c)[0] for c in text]
    w = int(sum(widths) + spacing * (len(text) - 1) + 2 * pad)
    top, bottom = f.getbbox("ODYSSEY")[1], f.getbbox("ODYSSEY")[3]
    h = int(bottom - top + 2 * pad)
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    x = pad
    for c, cw in zip(text, widths):
        d.text((x - f.getbbox(c)[0], pad - top), c, font=f, fill=255)
        x += cw + spacing
    return mask


def gold_leaf(mask):
    """Fill a text mask with gold leaf: cream highlight, gold body, a darker
    band low in the letters, and a crimson drop shadow behind."""
    w, h = mask.size
    box = mask.getbbox()
    grad = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(grad)
    for y in range(h):
        f = (y - box[1]) / max(1, box[3] - box[1])
        f = min(1, max(0, f))
        if f < 0.45:
            col = lerp(CREAM, GOLD_LIGHT, f / 0.45)
        elif f < 0.7:
            col = lerp(GOLD_LIGHT, GOLD, (f - 0.45) / 0.25)
        else:
            col = lerp(GOLD, GOLD_DARK, (f - 0.7) / 0.3)
        d.line([(0, y), (w, y)], fill=col + (255,))
    grad.putalpha(mask)
    shadow = Image.new("RGBA", (w, h), CRIMSON_DEEP + (0,))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(5 * S))
                    .point(lambda v: min(255, int(v * 1.4))))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(shadow, (3 * S, 4 * S))
    edge = Image.new("RGBA", (w, h), GOLD_DARK + (0,))
    edge.putalpha(mask.filter(ImageFilter.MaxFilter(3)))
    out.alpha_composite(edge)
    out.alpha_composite(grad)
    return out


def title_word(path):
    f = font("Georgia.ttf", 108)
    mask = spaced_mask("ODYSSEY", f, 10 * S, 14 * S)
    img = gold_leaf(mask)
    img.resize((img.width // S, img.height // S), Image.LANCZOS).save(path)


def banner(path, hover=False):
    """BEGIN VOYAGE on crimson cloth with a gold double border."""
    w, h = 300 * S, 62 * S
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (178, 76, 82) if hover else CRIMSON
    for y in range(h):                                  # cloth catching light
        f = abs(y / h - 0.4)
        d.line([(0, y), (w, y)], fill=lerp(base, CRIMSON_DEEP, f * 1.2) + (250,))
    for k in range(1, 12):                              # soft folds
        x = k * w / 12
        d.line([(x, 0), (x, h)], fill=CRIMSON_DEEP + (60,), width=S * 2)
    d.rectangle([0, 0, w - 1, h - 1], outline=GOLD_DARK + (255,), width=3 * S)
    d.rectangle([6 * S, 6 * S, w - 6 * S, h - 6 * S], outline=GOLD + (255,),
                width=S)
    for cx, cy in [(0, 0), (w, 0), (0, h), (w, h)]:
        r = 8 * S
        cx = min(max(cx, r), w - r)
        cy = min(max(cy, r), h - r)
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                  fill=GOLD_LIGHT + (255,))
    f = font("Georgia.ttf", 20)
    text = "BEGIN VOYAGE"
    mask = spaced_mask(text, f, 6 * S, 0)
    gold = gold_leaf(mask)
    img.alpha_composite(gold, ((w - gold.width) // 2,
                               (h - gold.height) // 2 + S))
    if hover:
        halo = img.filter(ImageFilter.GaussianBlur(6 * S))
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out.alpha_composite(halo)
        out.alpha_composite(img)
        img = out
    img.resize((w // S, h // S), Image.LANCZOS).save(path)


def build(folder):
    """Returns {name: path}; rebuilt only when VERSION changes."""
    paths = {n: os.path.join(folder, n + ".png")
             for n in ("odyssey", "banner", "banner_hover")}
    stamp = os.path.join(folder, "VERSION")
    if os.path.exists(stamp) and open(stamp).read() == VERSION and \
            all(os.path.exists(p) for p in paths.values()):
        return paths
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):                     # clear earlier versions
        if old.endswith(".png"):
            os.remove(os.path.join(folder, old))
    title_word(paths["odyssey"])
    banner(paths["banner"])
    banner(paths["banner_hover"], hover=True)
    with open(stamp, "w") as f:
        f.write(VERSION)
    return paths
