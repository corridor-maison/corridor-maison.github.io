"""Icônes et écrans de lancement dessinés depuis Kono (la constante KONO d'app/app.js), rendus par Chromium (Playwright).

Sorties :
- toujours : app/icons/icon-192.png, icon-512.png (usage « any », Kono à 82 % sur fond sable plein)
             et icon-maskable-192.png, icon-maskable-512.png (usage « maskable », Kono à 58 % : dans le cercle sûr de 80 %) ;
- --android <res> : dans le dossier res/ de l'enveloppe Android : mipmap-*/ic_launcher.png (tuile sable arrondie, 48 dp),
             mipmap-*/ic_maskable.png (fond plein, 82 dp, Kono dans le cercle visible de l'icône adaptative) et drawable-*/splash.png
             (300 dp, fond transparent : la couleur de fond de l'écran de lancement est celle de l'enveloppe, le sable) ;
- --play <dossier> : icone-512.png et banniere-1024x500.png pour la fiche Google Play.

Lancer : python3 tools/build_icons.py [--android C:/ca/corridor-android/app/src/main/res] [--play <dossier>]
Les yeux sont ouverts, sans sourcils, comme Kono au repos dans l'application.
"""
import argparse, asyncio, pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent; APP = ROOT / "app"
SAND = "#f6efe2"; PORT = 8791
DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
EYES = '<style>.k-lids,.k-eyes-happy,.k-brows{display:none}</style>'

def kono_svg():
    svg = re.search(r"const KONO = `(<svg.*?</svg>)`;", (APP / "app.js").read_text(encoding="utf-8"), re.S).group(1)
    return svg.replace('class="kono"', 'style="width:100%;height:100%;display:block"')

def kono_html(svg, w, h, bg, frac, radius=0):
    kh = h * frac; kw = kh * 200 / 212
    tile = f'<div style="position:absolute;inset:0;background:{SAND};border-radius:{radius}px"></div>' if radius else ""
    return (f'<!doctype html><html><head><meta charset="utf-8">{EYES}</head><body style="margin:0;width:{w}px;height:{h}px;background:{bg};overflow:hidden;position:relative">'
            f'{tile}<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:{kw:.2f}px;height:{kh:.2f}px">{svg}</div></body></html>')

def banner_html(svg):
    return f'''<!doctype html><html><head><meta charset="utf-8">{EYES}<style>
@font-face {{ font-family: Nunito; src: url(fonts/nunito-800.woff2) format("woff2"); font-weight: 800; }}
@font-face {{ font-family: Andika; src: url(fonts/andika-700.woff2) format("woff2"); font-weight: 700; }}
body {{ margin:0; width:1024px; height:500px; background:{SAND}; position:relative; overflow:hidden; font-family: Nunito, sans-serif; }}
.top {{ position:absolute; left:0; top:0; width:1024px; height:14px; background:#2f7ea6; }}
.bot {{ position:absolute; left:0; bottom:0; width:1024px; height:14px; background:#c35713; }}
.kono {{ position:absolute; left:70px; top:70px; width:{360 * 200 / 212:.1f}px; height:360px; }}
h1 {{ position:absolute; left:440px; top:120px; margin:0; font-size:78px; line-height:1.02; color:#1c5aa6; font-weight:800; }}
p {{ position:absolute; left:442px; top:318px; margin:0; font-family: Andika, sans-serif; font-weight:700; font-size:29px; line-height:1.3; color:#22303c; width:540px; }}
</style></head><body><div class="top"></div><div class="bot"></div><div class="kono">{svg}</div>
<h1>Corridor<br>à la maison</h1><p>Des séances guidées par la voix de Kono, pour apprendre en famille, sans internet.</p></body></html>'''

def jobs(android, play):
    svg = kono_svg(); out = []
    def add(name, html, w, h, transparent, dests): out.append((name, html, w, h, transparent, [pathlib.Path(d) for d in dests]))
    for s in (192, 512):
        add(f"any-{s}", kono_html(svg, s, s, SAND, .82), s, s, False, [APP / f"icons/icon-{s}.png"] + ([play / "icone-512.png"] if play and s == 512 else []))
        add(f"mask-{s}", kono_html(svg, s, s, SAND, .58), s, s, False, [APP / f"icons/icon-maskable-{s}.png"])
    if android:
        for d, k in DENS.items():
            s = round(48 * k); add(f"launcher-{d}", kono_html(svg, s, s, "transparent", .78, radius=s * .18), s, s, True, [android / f"mipmap-{d}/ic_launcher.png"])
            s = round(82 * k); add(f"maskable-{d}", kono_html(svg, s, s, SAND, .58), s, s, False, [android / f"mipmap-{d}/ic_maskable.png"])
            s = round(300 * k); add(f"splash-{d}", kono_html(svg, s, s, "transparent", .72), s, s, True, [android / f"drawable-{d}/splash.png"])
    if play: add("banniere", banner_html(svg), 1024, 500, False, [play / "banniere-1024x500.png"])
    return out

async def render(all_jobs):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="corridor-icones-")); shutil.copytree(APP / "fonts", tmp / "fonts")
    for name, html, *_ in all_jobs: (tmp / f"{name}.html").write_text(html, encoding="utf-8")
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--directory", str(tmp)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for name, html, w, h, transparent, dests in all_jobs:
                pg = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                await pg.goto(f"http://localhost:{PORT}/{name}.html"); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(150)
                png = await pg.screenshot(omit_background=transparent, type="png"); await pg.close()
                for d in dests: d.parent.mkdir(parents=True, exist_ok=True); d.write_bytes(png); print(f"{name:16} {w}×{h} → {d}")
            await b.close()
    finally:
        srv.terminate(); shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--android", type=pathlib.Path); ap.add_argument("--play", type=pathlib.Path); a = ap.parse_args()
    asyncio.run(render(jobs(a.android, a.play)))
