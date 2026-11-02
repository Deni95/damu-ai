"""Минималистичное видео-поздравление с днём рождения: «Дарю тебе своё сердце».
Запуск: python3 make_video.py  ->  love_video.mp4
Тексты можно поменять в списке SCENES ниже."""
import math, subprocess, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT_W, OUT_H, SS = 720, 1280, 2
W, H = OUT_W * SS, OUT_H * SS
FPS, DUR = 30, 22.0
HERE = os.path.dirname(os.path.abspath(__file__))
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SERIF_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

BG = (248, 244, 239)
INK = (60, 50, 54)
RED = (200, 36, 58)

# (текст, начало, конец, размер, y, шрифт, цвет)
SCENES = [
    ("сегодня твой день", 0.5, 3.8, 40, 640, SERIF_I, INK),
    ("у меня есть для тебя подарок", 4.2, 8.3, 30, 930, SERIF_I, INK),
    ("моё сердце", 8.6, 12.1, 34, 930, SERIF_I, INK),
    ("оно навсегда твоё", 12.4, 15.6, 34, 930, SERIF_I, INK),
    ("С днём рождения,\nлюбимая", 16.0, DUR + 1, 52, 820, SERIF, INK),
    ("я тебя люблю", 17.4, DUR + 1, 28, 1000, SERIF_I, RED),
]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def window(t, a, b, f=0.8): return ease((t - a) / f) * (1 - ease((t - (b - f)) / f))

def heart_xy(th):
    x = 16 * math.sin(th) ** 3
    y = -(13 * math.cos(th) - 5 * math.cos(2 * th) - 2 * math.cos(3 * th) - math.cos(4 * th))
    return x / 17, y / 17

# одна непрерывная линия: слева -> обводит сердце -> уходит вправо
CX, CY0, S0 = W / 2, H * 0.42, 150 * SS
def build_path(cx, cy, s):
    tip = (cx, cy + s * 1.0)
    pts = [(-40 * SS, tip[1])]
    pts += [(lerpv, tip[1]) for lerpv in np.linspace(-40 * SS, tip[0], 60)[1:]]
    for th in np.linspace(math.pi, 3 * math.pi, 240):
        x, y = heart_xy(th); pts.append((cx + x * s, cy + y * s))
    pts += [(v, tip[1]) for v in np.linspace(tip[0], W + 40 * SS, 60)[1:]]
    seg = [0.0]
    for a, b in zip(pts, pts[1:]): seg.append(seg[-1] + math.dist(a, b))
    return pts, seg
PATH, SEG = build_path(CX, CY0, S0)
HEART_START, HEART_END = 59, 59 + 239

def partial(pts, seg, frac):
    L = seg[-1] * frac
    out = [p for p, l in zip(pts, seg) if l <= L]
    return out

def heart_poly(cx, cy, s):
    return [(cx + x * s, cy + y * s) for x, y in (heart_xy(2 * math.pi * i / 160) for i in range(160))]

FONTS = {}
def font(path, size):
    k = (path, size)
    if k not in FONTS: FONTS[k] = ImageFont.truetype(path, size * SS)
    return FONTS[k]

def render(t):
    img = Image.new("RGB", (W, H), BG)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)

    # сердце поднимается в финале
    up = ease((t - 15.6) / 1.4)
    cy = CY0 - up * 120 * SS
    lw = 3 * SS

    # 1) линия рисуется
    draw_k = ease((t - 4.0) / 3.6)
    side_a = 1 - ease((t - 8.4) / 1.0)          # горизонтальные хвосты исчезают
    if draw_k > 0:
        pts = partial(PATH, SEG, draw_k)
        dy = cy - CY0
        pts = [(x, y + dy) for x, y in pts]
        if len(pts) > 1:
            n = len(pts)
            left = pts[:min(n, HEART_START + 1)]
            mid = pts[HEART_START:min(n, HEART_END + 1)] if n > HEART_START else []
            right = pts[HEART_END:] if n > HEART_END else []
            ca = INK + (int(255 * side_a),)
            if len(left) > 1 and side_a > 0: d.line(left, fill=ca, width=lw)
            if len(right) > 1 and side_a > 0: d.line(right, fill=ca, width=lw)
            if len(mid) > 1:
                outline_a = 1 - ease((t - 9.2) / 0.8)
                if outline_a > 0: d.line(mid, fill=INK + (int(255 * outline_a),), width=lw, joint="curve")

    # 2) сердце заливается красным и тихо бьётся
    fill_k = ease((t - 8.6) / 1.2)
    if fill_k > 0:
        tb = t - 9.8
        beat = 1 + (0.045 * math.exp(-((tb % 1.1) - 0.0) * 7) + 0.03 * math.exp(-((tb % 1.1) - 0.22) ** 2 * 300)) * (tb > 0)
        s = S0 * beat
        d.polygon(heart_poly(CX, cy, s), fill=RED + (int(255 * fill_k),))

    img.paste(lay, (0, 0), lay)

    # тексты
    for txt, a, b, size, y, fp, col in SCENES:
        al = window(t, a, b)
        if al <= 0: continue
        tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(tl).multiline_text((W // 2, (y + (1 - ease((t - a) / 1.0)) * 12) * SS), txt,
                                          font=font(fp, size), fill=col + (int(255 * al),),
                                          anchor="ma", align="center", spacing=18 * SS)
        img.paste(tl, (0, 0), tl)

    img = img.resize((OUT_W, OUT_H), Image.LANCZOS)
    f = min(ease(t / 0.8), 1 - ease((t - (DUR - 1.5)) / 1.5))
    if f < 1: img = Image.blend(Image.new("RGB", img.size, BG), img, f)
    return img

# тихая фортепианная мелодия (оригинальная)
def make_music(path):
    sr = 44100; n = int(sr * DUR); out = np.zeros(n)
    def note(t0, midi, dur, vol):
        f = 440 * 2 ** ((midi - 69) / 12); i0 = int(t0 * sr)
        if i0 >= n: return
        L = min(int(dur * sr), n - i0); tt = np.arange(L) / sr
        env = np.exp(-tt * 1.8) * np.minimum(1, tt * 120)
        w = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 3)
        out[i0:i0 + L] += w * env * vol
    bars = [([48, 55, 64], [67, None, 64, 72]), ([45, 52, 60], [69, None, 67, 64]),
            ([41, 48, 57], [65, None, 64, 60]), ([43, 50, 59], [62, None, 67, None])]
    beat = 0.85; t = 0.3; i = 0
    while t < DUR:
        ch, mel = bars[i % 4]
        for j, m in enumerate(ch): note(t + j * 0.06, m, 3.5, 0.12)
        for j, m in enumerate(mel):
            if m: note(t + j * beat, m, 2.5, 0.22)
        t += 4 * beat; i += 1
    d = int(0.31 * sr); wet = out.copy()
    for k in range(1, 6): wet[d * k:] += out[:-d * k] * (0.33 ** k)
    fl = int(2.5 * sr); wet[-fl:] *= np.linspace(1, 0, fl)
    wet /= np.abs(wet).max() * 1.3
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((wet * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    wav = os.path.join(HERE, "_music.wav"); make_music(wav)
    out = os.path.join(HERE, "love_video.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-i", wav,
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    for i in range(total):
        p.stdin.write(render(i / FPS).tobytes())
    p.stdin.close(); p.wait(); os.remove(wav)
    print("done:", out)
