#!/usr/bin/env python3
"""Compose shareable 1200x630 cover cards from key lesson figures.

Local-only (uses chromium for PNG). Outputs (committed):
  assets/covers/<slug>.svg   source of truth
  assets/covers/<slug>.png   rendered 2x
  assets/covers.html         gallery

Usage:
  python3 build_covers.py            build all covers + gallery
  python3 build_covers.py --list 03  list lesson 03's zh figures (pick index)
"""
import base64
import glob
import html as _html
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
LESSONS = os.path.join(ROOT, "lessons")
OUT = os.path.join(ROOT, "assets", "covers")
sys.path.insert(0, HERE)
import shell  # noqa: E402  (palette + favicon + lang JS)

# (lesson, lang, fig_index_within_that_lang, slug, title_zh, title_en)
# fig_index defaults to 0 (the lesson's headline figure); verify with --list.
COVERS = [
    ("57", "zh", 0, "01-life-of-a-row", "一条数据的一生", "Life of a row"),
    ("09", "zh", 0, "02-control-data-plane", "控制面 vs 数据面", "Control plane vs data plane"),
    ("51", "zh", 0, "03-log-as-data", "日志即数据", "Log as data"),
    ("12", "zh", 0, "04-segment-lifecycle", "段的生命周期", "Segment lifecycle"),
    ("26", "zh", 0, "05-two-layer-fanout", "两层扇出查询", "Two-layer fan-out query"),
    ("53", "zh", 0, "06-storage-compute", "存算分离", "Storage-compute separation"),
]


def parse_palette(css):
    """{var: value}; dark :root overlaid on the light :root defaults."""
    pal = {}
    m = re.search(r":root\s*\{(.*?)\}", css, re.S)
    if m:
        for k, v in re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)):
            pal[k] = v.strip()
    md = re.search(r"@media \(prefers-color-scheme: dark\)\s*\{(.*)\}", css, re.S)
    if md:
        dm = re.search(r":root\s*\{(.*?)\}", md.group(1), re.S)
        if dm:
            for k, v in re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", dm.group(1)):
                pal[k] = v.strip()
    return pal


def inline_palette(svg, pal):
    return re.sub(r"var\(--([a-z0-9-]+)(?:\s*,[^)]*)?\)",
                  lambda m: pal.get(m.group(1), "#888"), svg)


def figs_of(lesson, lang):
    f = glob.glob(os.path.join(LESSONS, f"{lesson}-*.html"))[0]
    h = open(f, encoding="utf-8").read()
    figs = re.findall(r'<div class="fig">.*?</div>\s*</div>', h, re.S)
    half = len(figs) // 2
    return figs[:half] if lang == "zh" else figs[half:]


def inner_svg(fig):
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', fig, re.S)
    if not m:
        raise SystemExit("build_covers: could not parse <svg> in figure")
    return m.group(1), m.group(2)


def build_svg(lesson, lang, idx, tz, te, pal):
    figs = figs_of(lesson, lang)
    if idx >= len(figs):
        raise SystemExit(f"build_covers: lesson {lesson} has {len(figs)} {lang} figs, need idx {idx}")
    vb, inner = inner_svg(figs[idx])
    inner = inline_palette(inner, pal)
    bg = pal.get("bg", "#0e1117")
    ink = pal.get("ink", "#e6e6e6")
    muted = pal.get("muted", "#9aa0a6")
    accent = pal.get("accent", "#1296db")
    panel = pal.get("panel", "#171a21")
    line = pal.get("line", "#2a2f37")
    W, H, fw = 1200, 630, 976
    fh = int(fw * 300 / 760)
    fx = (W - fw) // 2
    fy = 170
    font = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>text{{font-family:{font}}}svg svg text{{fill:{ink}}}.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}</style>
<rect width="{W}" height="{H}" fill="{bg}"/>
<rect x="0" y="0" width="{W}" height="8" fill="{accent}"/>
<text x="60" y="66" font-size="30" font-weight="700" fill="{ink}">🐦 Milvus 图解教程 · Milvus Visual Guide</text>
<text x="60" y="112" font-size="36" font-weight="700" fill="{accent}">第 {int(lesson)} 课 · {_html.escape(tz)}</text>
<text x="60" y="142" font-size="22" fill="{muted}">{_html.escape(te)}</text>
<rect x="{fx - 20}" y="{fy - 16}" width="{fw + 40}" height="{fh + 32}" rx="16" fill="{panel}" stroke="{line}"/>
<svg x="{fx}" y="{fy}" width="{fw}" height="{fh}" viewBox="{vb}">{inner}</svg>
<text x="60" y="{H - 32}" font-size="22" fill="{muted}">verdenmax.github.io/milvus-visual-guide</text>
<text x="{W - 60}" y="{H - 32}" text-anchor="end" font-size="22" fill="{muted}">57 课 · 中英双语 / bilingual</text>
</svg>'''


def _which(b):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.exists(os.path.join(p, b)):
            return True
    return False


def render_png(svg_path, png_path):
    if not _which("chromium"):
        print("  (chromium not found; skipping PNG — commit SVG only)")
        return False
    try:
        from PIL import Image
    except Exception:
        print("  (Pillow not available; skipping PNG)")
        return False
    svg = open(svg_path, encoding="utf-8").read()
    b64 = base64.b64encode(svg.encode()).decode()
    # Embed as a fixed-size <img> (renders the SVG at exact pixel dims), placed
    # top-left in a window LARGER than the card, then crop the exact 2400x1260
    # region. This sidesteps chromium's flaky standalone-SVG viewport sizing
    # (short/tiled/edge-artefact renders) entirely.
    doc = ('<!doctype html><meta charset="utf-8">'
           '<style>*{margin:0;padding:0}img{display:block}</style>'
           f'<img src="data:image/svg+xml;base64,{b64}" width="1200" height="630">')
    udd = tempfile.mkdtemp(prefix="cov_")
    htmlpath = os.path.join(udd, "cover.html")
    rawpath = os.path.join(udd, "raw.png")
    open(htmlpath, "w", encoding="utf-8").write(doc)
    subprocess.run(["chromium", "--headless", "--no-sandbox", "--hide-scrollbars",
                    f"--user-data-dir={udd}", "--force-device-scale-factor=2",
                    "--window-size=1360,760", f"--screenshot={rawpath}", htmlpath],
                   capture_output=True)
    if not os.path.exists(rawpath):
        return False
    Image.open(rawpath).convert("RGB").crop((0, 0, 2400, 1260)).save(png_path)
    return True


def _slug_lookup(lesson):
    f = glob.glob(os.path.join(LESSONS, f"{lesson}-*.html"))[0]
    return os.path.basename(f).split("-", 1)[1]


def gallery_html():
    cards = []
    for lesson, lang, idx, slug, tz, te in COVERS:
        cards.append(
            f'<figure class="cov"><a href="assets/covers/{slug}.png"><img loading="lazy" '
            f'src="assets/covers/{slug}.png" alt="{_html.escape(tz)} / {_html.escape(te)}"></a>'
            f'<figcaption><b>第 {int(lesson)} 课 · <span class="lang-zh">{_html.escape(tz)}</span>'
            f'<span class="lang-en">{_html.escape(te)}</span></b><br>'
            f'<a href="assets/covers/{slug}.svg" download>SVG</a> · '
            f'<a href="assets/covers/{slug}.png" download>PNG</a> · '
            f'<a href="lessons/{lesson}-{_slug_lookup(lesson)}"><span class="lang-zh">看这一课</span>'
            f'<span class="lang-en">open lesson</span></a></figcaption></figure>')
    grid = "\n".join(cards)
    return f'''<!DOCTYPE html>
<html lang="zh-CN" data-lang="zh"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{shell.LANG_BOOT}
<title>封面图库 · Cover gallery - Milvus 图解教程</title>
{shell.head_meta("封面图库 · Cover gallery - Milvus 图解教程", "Shareable 1200x630 cover cards of the Milvus Visual Guide's key diagrams (SVG + PNG).")}
<style>{shell.CSS}
.covgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:1.4rem;margin:1.6rem 0}}
.cov{{margin:0}}
.cov img{{width:100%;border:1px solid var(--line);border-radius:12px;display:block}}
.cov figcaption{{color:var(--muted);font-size:.9rem;margin:.5rem 0 0}}
</style></head><body>
<div class="topbar"><div class="topbar-inner">
<a class="home" href="index.html">🐦 <b class="lang-zh">Milvus 图解教程</b><b class="lang-en">Milvus Visual Guide</b></a>
<span class="pill"><span class="lang-zh">封面图库</span><span class="lang-en">Cover gallery</span></span>
<button class="langtoggle" onclick="mvgToggleLang()" aria-label="switch language"><span class="lang-zh">EN</span><span class="lang-en">中</span></button>
</div><div class="progress"><span style="width:100%"></span></div></div>
<div class="wrap"><div class="hero">
<div class="part">{shell.bi("可分享封面", "Shareable covers")}</div>
<h1><span class="lang-zh">封面图库</span><span class="lang-en">Cover gallery</span></h1>
<p class="lead">{shell.bi("把本教程最具代表性的几张图做成 1200×630 的可分享封面（社交卡片尺寸）。点击看大图，或下载 SVG / PNG。", "The guide's most iconic diagrams as 1200×630 shareable cards (social-card size). Click to enlarge, or download SVG / PNG.")}</p>
</div>
<div class="covgrid">{grid}</div>
</div>
<script>{shell.LANG_JS}</script>
</body></html>'''


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--list":
        for i, fig in enumerate(figs_of(sys.argv[2], "zh")):
            m = re.search(r'aria-label="([^"]*)"', fig)
            print(f"[{i}] {(m.group(1) if m else '(no aria)')[:90]}")
        return
    os.makedirs(OUT, exist_ok=True)
    pal = parse_palette(shell.CSS)
    for lesson, lang, idx, slug, tz, te in COVERS:
        svg = build_svg(lesson, lang, idx, tz, te, pal)
        sp = os.path.join(OUT, slug + ".svg")
        open(sp, "w", encoding="utf-8").write(svg)
        ok = render_png(sp, os.path.join(OUT, slug + ".png"))
        print(f"  {slug}.svg{' + .png' if ok else ''}")
    open(os.path.join(ROOT, "covers.html"), "w", encoding="utf-8").write(gallery_html())
    print(f"Wrote {len(COVERS)} covers + covers.html")


if __name__ == "__main__":
    main()
