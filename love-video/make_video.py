"""Милое видео-поздравление: «Дарю тебе своё сердце».
Запуск: python3 make_video.py  ->  love_video.mp4
Тексты можно поменять в словаре TEXTS ниже."""
import math, random, subprocess, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TEXTS = {
    "intro":  "Моей самой\nлюбимой девочке",
    "gift":   "У меня есть для тебя\nособенный подарок...",
    "heart":  "Это моё сердце",
    "yours":  "Теперь оно\nнавсегда твоё",
    "final1": "Поздравляю тебя,\nлюбимая!",
    "final2": "Я тебя люблю",
}

OUT_W, OUT_H, SS = 720, 1280, 2
W, H = OUT_W * SS, OUT_H * SS
FPS, DUR = 30, 23.0
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"
if not os.path.exists(FONT_I):
    FONT_I = FONT_B
random.seed(7)

# ---------- helpers ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def back_out(x):
    x = clamp(x); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def window(t, a, b, fade=0.6):
    return ease((t - a) / fade) * (1 - ease((t - (b - fade)) / fade))
def lerp(a, b, k): return a + (b - a) * k

HEART_PTS = []
for i in range(120):
    th = 2 * math.pi * i / 120
    x = 16 * math.sin(th) ** 3
    y = -(13 * math.cos(th) - 5 * math.cos(2 * th) - 2 * math.cos(3 * th) - math.cos(4 * th))
    HEART_PTS.append((x / 17, y / 17))

def heart(d, cx, cy, s, fill, rot=0.0):
    c, sn = math.cos(rot), math.sin(rot)
    pts = [(cx + (x * c - y * sn) * s, cy + (x * sn + y * c) * s) for x, y in HEART_PTS]
    d.polygon(pts, fill=fill)

def fade_layer(layer, a):
    if a >= 0.999: return layer
    al = layer.getchannel("A").point(lambda v: int(v * a))
    layer.putalpha(al); return layer

def text_layer(txt, size, y, color=(255, 255, 255), font=FONT_B, glow=(214, 51, 108)):
    f = ImageFont.truetype(font, size * SS)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.multiline_text((W // 2, y * SS), txt, font=f, fill=color + (255,), anchor="ma",
                     align="center", spacing=14 * SS, stroke_width=5 * SS, stroke_fill=glow + (255,))
    return lay

# ---------- background ----------
yy = np.linspace(0, 1, H)[:, None]
top, bot = np.array([255, 214, 226]), np.array([255, 160, 190])
g = (top[None, :] * (1 - yy) + bot[None, :] * yy)
BG = Image.fromarray(np.repeat(g[:, None, :], W, axis=1).astype(np.uint8), "RGB").convert("RGBA")

particles = [dict(x=random.uniform(0, W), y0=random.uniform(0, H), sp=random.uniform(60, 160) * SS,
                  s=random.uniform(12, 34) * SS, ph=random.uniform(0, 6.28),
                  col=random.choice([(255, 255, 255), (255, 120, 160), (255, 80, 130), (255, 190, 210)]),
                  a=random.randint(90, 190)) for _ in range(38)]

def draw_particles(t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for p in particles:
        y = (p["y0"] - p["sp"] * t) % (H + 200) - 100
        x = p["x"] + math.sin(t * 1.3 + p["ph"]) * 30 * SS
        heart(d, x, y, p["s"], p["col"] + (p["a"],), rot=math.sin(t + p["ph"]) * 0.3)
    return lay

# ---------- characters ----------
def character(d, cx, cy, body, t, girl=False, blush=0.0, look=0.0):
    bob = math.sin(t * 3 + (1 if girl else 0)) * 8 * SS
    cy += bob
    rx, ry = 160 * SS, 185 * SS
    # shadow
    d.ellipse((cx - rx * 0.8, cy + ry - 20 * SS - bob, cx + rx * 0.8, cy + ry + 30 * SS - bob), fill=(200, 90, 130, 70))
    # arms
    arm = body
    d.ellipse((cx - rx - 25 * SS, cy + 20 * SS, cx - rx + 55 * SS, cy + 110 * SS), fill=arm)
    d.ellipse((cx + rx - 55 * SS, cy + 20 * SS, cx + rx + 25 * SS, cy + 110 * SS), fill=arm)
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=body)
    # feet
    for sx in (-1, 1):
        d.ellipse((cx + sx * 80 * SS - 55 * SS, cy + ry - 40 * SS, cx + sx * 80 * SS + 55 * SS, cy + ry + 25 * SS), fill=body)
    # eyes (blink)
    blink = 1.0
    ph = (t + (0.7 if girl else 0)) % 3.4
    if ph < 0.15: blink = 0.12
    ex = 62 * SS; ey = cy - 40 * SS; lx = look * 18 * SS
    for sx in (-1, 1):
        x = cx + sx * ex + lx
        h = 34 * SS * blink
        d.ellipse((x - 24 * SS, ey - h, x + 24 * SS, ey + h), fill=(50, 30, 45))
        if blink > 0.5:
            d.ellipse((x - 10 * SS, ey - 22 * SS, x + 6 * SS, ey - 6 * SS), fill=(255, 255, 255))
        if girl and blink > 0.5:  # lashes
            d.line((x + sx * 20 * SS, ey - 26 * SS, x + sx * 36 * SS, ey - 40 * SS), fill=(50, 30, 45), width=6 * SS)
    # cheeks
    ca = int(110 + 130 * blush)
    for sx in (-1, 1):
        x = cx + sx * 100 * SS + lx * 0.5
        d.ellipse((x - 34 * SS, cy + 5 * SS, x + 34 * SS, cy + 35 * SS), fill=(255, 90, 130, ca))
    # smile
    d.arc((cx - 34 * SS + lx, cy - 5 * SS, cx + 34 * SS + lx, cy + 45 * SS), 20, 160, fill=(80, 30, 50), width=8 * SS)
    if girl:  # bow
        bx, by = cx + 95 * SS, cy - ry + 40 * SS
        d.polygon([(bx, by), (bx - 75 * SS, by - 50 * SS), (bx - 70 * SS, by + 45 * SS)], fill=(235, 50, 100))
        d.polygon([(bx, by), (bx + 75 * SS, by - 50 * SS), (bx + 70 * SS, by + 45 * SS)], fill=(235, 50, 100))
        d.ellipse((bx - 22 * SS, by - 22 * SS, bx + 22 * SS, by + 22 * SS), fill=(255, 90, 140))
    else:  # hair tuft
        d.arc((cx - 40 * SS, cy - ry - 50 * SS, cx + 40 * SS, cy - ry + 30 * SS), 200, 340, fill=body, width=16 * SS)
    return cy

BOY = (W * 0.26, H * 0.70); GIRL = (W * 0.74, H * 0.70)
sparks = [(random.uniform(0, 6.28), random.uniform(120, 260) * SS, random.uniform(10, 22) * SS) for _ in range(26)]

def render(t):
    fr = BG.copy()
    fr.alpha_composite(draw_particles(t))

    # characters
    ca = ease((t - 2.4) / 0.9) * (1 - ease((t - 14.2) / 1.0))
    slide = ease((t - 14.2) / 1.2) * 500 * SS
    heart_x = heart_y = None
    if ca > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        look_b = 1.0 if 5 < t < 14 else 0.4
        look_g = -1.0 if 7 < t < 11.5 else -0.4
        blush_g = clamp((t - 10.5) / 1.5)
        character(d, BOY[0], BOY[1] + slide, (142, 197, 255), t, look=look_b, blush=0.3)
        character(d, GIRL[0], GIRL[1] + slide, (255, 190, 210), t, girl=True, blush=blush_g, look=look_g)
        fr.alpha_composite(fade_layer(lay, ca))

    # travelling heart (7s .. 14.5s)
    if 7.0 <= t < 15.0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        appear = back_out((t - 7.0) / 0.8)
        beat = 1 + 0.08 * max(0, math.sin(t * 9)) ** 4
        sx, sy = BOY[0], BOY[1] - 20 * SS
        ex, ey = GIRL[0] - 30 * SS, GIRL[1] - 390 * SS
        k = ease((t - 9.0) / 2.3)
        x = lerp(sx, ex, k)
        y = lerp(sy - 280 * SS * appear, ey, k) - math.sin(k * math.pi) * 260 * SS
        s = 95 * SS * appear * beat
        a = 1 - ease((t - 14.2) / 0.8)
        # glow
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        heart(gd, x, y, s * 1.35, (255, 255, 255, 150))
        fr.alpha_composite(fade_layer(glow.filter(ImageFilter.GaussianBlur(18 * SS)), a))
        heart(d, x, y, s, (235, 30, 80, 255))
        heart(d, x - s * 0.35, y - s * 0.35, s * 0.22, (255, 160, 190, 230))
        # sparkles when it lands
        if t > 11.3:
            pk = clamp((t - 11.3) / 1.6)
            for ang, r, ss in sparks:
                rr = r * ease(pk)
                heart(d, x + math.cos(ang) * rr, y + math.sin(ang) * rr, ss * (1 - pk), (255, 80, 130, 230))
        fr.alpha_composite(fade_layer(lay, a))

    # big heart finale
    if t >= 14.4:
        k = back_out((t - 14.4) / 1.3)
        beat = 1 + 0.06 * max(0, math.sin((t - 14.4) * 6)) ** 6
        x, y = W / 2, H * 0.55
        s = 255 * SS * k * beat
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        heart(gd, x, y, s * 1.2, (255, 255, 255, 170))
        fr.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30 * SS)))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        heart(d, x, y, s, (230, 25, 75, 255))
        heart(d, x - s * 0.38, y - s * 0.38, s * 0.18, (255, 160, 190, 220))
        # confetti hearts burst
        if t > 15.4:
            for i, (ang, r, ss) in enumerate(sparks):
                pk = ((t - 15.4) * 0.35 + i / len(sparks)) % 1.0
                rr = s * 0.9 + r * 3 * pk
                heart(d, x + math.cos(ang) * rr, y + math.sin(ang) * rr, ss * 1.4 * (1 - pk),
                      (255, 255, 255, int(220 * (1 - pk))))
        fr.alpha_composite(lay)

    # texts
    for key, a, b, size, y, font in [
        ("intro", 0.3, 4.2, 54, 330, FONT_I),
        ("gift", 4.2, 7.6, 44, 230, FONT_B),
        ("heart", 7.6, 11.2, 52, 230, FONT_I),
        ("yours", 11.2, 14.6, 52, 210, FONT_I),
        ("final1", 15.3, DUR + 1, 54, 150, FONT_I),
    ]:
        al = window(t, a, b)
        if al > 0:
            fr.alpha_composite(fade_layer(text_layer(TEXTS[key], size, y + (1 - ease((t - a) / 0.6)) * 30), al))
    al = window(t, 16.6, DUR + 1)
    if al > 0:
        fr.alpha_composite(fade_layer(text_layer(TEXTS["final2"], 58, 680, color=(255, 255, 255),
                                                 font=FONT_I, glow=(170, 10, 55)), al))

    # global fade in/out
    img = fr.convert("RGB").resize((OUT_W, OUT_H), Image.LANCZOS)
    f = min(ease(t / 0.8), 1 - ease((t - (DUR - 1.2)) / 1.2))
    if f < 1:
        img = Image.blend(Image.new("RGB", img.size, (255, 255, 255)), img, f)
    return img

# ---------- music: original soft music-box melody ----------
def make_music(path):
    sr = 44100; n = int(sr * DUR); out = np.zeros(n)
    def note(t0, midi, dur, vol):
        f = 440 * 2 ** ((midi - 69) / 12)
        i0 = int(t0 * sr); L = int(dur * sr)
        if i0 >= n: return
        L = min(L, n - i0); tt = np.arange(L) / sr
        env = np.exp(-tt * 3.2) * np.minimum(1, tt * 200)
        w = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)
        out[i0:i0 + L] += w * env * vol
    beat = 0.5
    chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]  # C Am F G
    melody = [76, 74, 72, 74, 76, 76, 76, None, 74, 72, 69, 72, 74, 76, 77, None,
              77, 76, 72, 69, 72, 74, 72, None, 74, 76, 79, 77, 76, 74, 72, None]
    t = 0.0; bar = 0
    while t < DUR:
        ch = chords[bar % 4]
        for j, m in enumerate(ch + [ch[1] + 12]):
            note(t + j * beat, m - 12, 1.6, 0.18)
        for j in range(4):
            m = melody[(bar * 4 + j) % len(melody)]
            if m: note(t + j * beat, m, 1.2, 0.26)
        t += 4 * beat; bar += 1
    # reverb-ish echo
    d = int(0.23 * sr); wet = out.copy()
    for k in range(1, 5): wet[d * k:] += out[:-d * k] * (0.35 ** k)
    fade = np.ones(n); fl = int(2.0 * sr); fade[-fl:] = np.linspace(1, 0, fl); fade[:int(0.5 * sr)] = np.linspace(0, 1, int(0.5 * sr))
    wet *= fade; wet /= np.abs(wet).max() * 1.15
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((wet * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    wav = os.path.join(HERE, "_music.wav"); make_music(wav)
    out = os.path.join(HERE, "love_video.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-i", wav,
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    for i in range(total):
        p.stdin.write(render(i / FPS).tobytes())
        if i % 60 == 0: print(f"{i}/{total}", flush=True)
    p.stdin.close(); p.wait(); os.remove(wav)
    print("done:", out)
