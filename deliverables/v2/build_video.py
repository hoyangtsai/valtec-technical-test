#!/usr/bin/env python3
"""Cut the CleanShot X take into the <3 min acceptance video.

Waits are sped up (never left as still frames); every segment gets a caption bar
below the recorded 1600x900 area; intro/outro cards are rendered with Pillow.
"""
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
RAW = HERE / "raw-cleanshot.mp4"
OUT = HERE / "valtec-acceptance-v2.mp4"
BUILD = HERE / "build"
W, H, BAR = 1600, 900, 100
OFFSET = 0.4            # recorded video time = script mark time - OFFSET (measured from first terminal change)
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
MONO = "/System/Library/Fonts/Menlo.ttc"
BG, FG, ACCENT, MUTED = (11, 18, 32), (241, 245, 249), (34, 197, 94), (148, 163, 184)

# (mark_start, mark_end, speed, title, detail)
SEGMENTS = [
    (1.3,   5.3, 1.0, "1 · Project architecture", "ArduPilot Quad SITL + MAVLink-router + FastAPI, controlled from QGroundControl"),
    (5.3,  14.6, 1.3, "1 · One-command start", "docker compose down  →  up --build -d  →  ps"),
    (14.6, 37.0, 6.0, "Waiting for the simulator to boot", "6× speed · container turns healthy, QGC reconnects and shows Ready"),
    (37.0, 40.1, 1.0, "Container healthy", "docker compose ps → (healthy) · QGroundControl: Ready"),
    (40.1, 48.2, 1.6, "2 · GET /status", "Swagger UI → Try it out → Execute"),
    (48.2, 51.3, 0.8, "HTTP 200 · armed: false · relative_altitude_m ≈ 0", "QGC: Ready, on the ground at the launch point"),
    (51.3, 65.4, 1.6, "3 · POST /takeoff   {\"altitude_m\": 3}", "Swagger UI → Try it out → edit body → Execute"),
    (65.4, 74.4, 3.0, "Takeoff in progress", "3× speed · QGC: vehicle arms and climbs to 3 m"),
    (74.4, 78.0, 0.8, "HTTP 200 · \"Takeoff completed at about 3.0 m\"", "QGC shows Flying / Guided, altitude 3 m"),
    (78.0, 88.1, 1.6, "4 · POST /land", "Swagger UI → Try it out → Execute"),
    (88.1, 100.1, 3.0, "Landing in progress", "3× speed · QGC: vehicle descends in place"),
    (100.1, 103.6, 0.8, "HTTP 200 · \"Landing completed and vehicle disarmed\"", "QGC is back to Ready"),
    (103.6, 117.7, 1.6, "5 · POST /takeoff again   {\"altitude_m\": 3}", "Swagger UI → Try it out → edit body → Execute"),
    (117.7, 126.7, 3.0, "Takeoff in progress", "3× speed · QGC: vehicle arms and climbs to 3 m"),
    (126.7, 130.2, 0.8, "HTTP 200 · \"Takeoff completed at about 3.0 m\"", "QGC shows Flying / Guided, altitude 3 m"),
    (130.2, 136.9, 1.3, "6 · QGroundControl Go To (about 24 m away)", "Click a point on the QGC map → Go to location → confirm slider"),
    (136.9, 142.0, 1.2, "Vehicle flying to the QGC target", "Manual Go To issued from QGC — the same simulated vehicle moves"),
    (142.0, 144.9, 2.0, "Vehicle reached the QGC target", "Position now differs from the API's previous one"),
    (144.9, 157.1, 1.6, "GET /status after the QGC Go To", "Swagger UI → Try it out → Execute"),
    (157.1, 160.2, 0.8, "HTTP 200 · new latitude / longitude", "The API reads back the position set by QGC's Go To"),
    (160.2, 176.6, 1.6, "7 · POST /goto   {latitude, longitude, altitude_m: 3}", "Swagger UI → Try it out → edit body → Execute"),
    (176.6, 185.6, 3.0, "Flying to the API target", "3× speed · QGC: vehicle moves to the position given by the API"),
    (185.6, 189.1, 0.8, "HTTP 200 · \"Target position reached\"", "distance_to_target_m ≈ 1 m · QGC shows the new position"),
    (189.1, 199.2, 1.5, "8 · POST /rtl", "Swagger UI → Try it out → Execute"),
    (199.2, 215.0, 2.5, "RTL in progress", "2.5× speed · vehicle climbs and returns to the launch point"),
    (215.0, 245.5, 8.0, "RTL: automatic landing", "8× speed · QGC altitude counts down from 15 m to 0"),
    (245.5, 249.7, 2.0, "RTL: touchdown and disarm", "2× speed · QGC switches to Ready"),
    (249.7, 252.7, 0.8, "HTTP 200 · \"RTL completed; vehicle landed and disarmed\"", "QGC shows Ready at the launch point"),
    (252.7, 264.7, 1.6, "9 · GET /status", "Swagger UI → Try it out → Execute"),
    (264.7, 267.8, 0.8, "HTTP 200 · armed: false · altitude ≈ 0 m", "Final state: landed and disarmed · QGC: Ready"),
    (267.8, 271.1, 1.0, "All four control APIs verified", "takeoff · goto · rtl · land — alternating with QGroundControl · container still healthy"),
]

def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)

def caption(i, title, detail, speed):
    im = Image.new("RGB", (W, BAR), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 3], fill=ACCENT)
    d.text((28, 16), title, font=font(FONT, 34), fill=FG)
    d.text((28, 64), detail, font=font(FONT, 22), fill=MUTED)
    if speed > 1.05:
        label = f"{speed:g}× speed"
        f = font(FONT, 24)
        w = d.textlength(label, font=f)
        d.rounded_rectangle([W - w - 60, 30, W - 24, 70], radius=10, fill=(30, 41, 59))
        d.text((W - w - 42, 35), label, font=f, fill=ACCENT)
    p = BUILD / f"cap{i:02d}.png"
    im.save(p)
    return p

def card(name, lines):
    im = Image.new("RGB", (W, H + BAR), BG)
    d = ImageDraw.Draw(im)
    y = 330
    for text, size, color in lines:
        f = font(FONT, size) if not text.startswith("`") else font(MONO, size, 0)
        text = text.strip("`")
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, y), text, font=f, fill=color)
        y += int(size * 1.7)
    p = BUILD / f"{name}.png"
    im.save(p)
    return p

def main():
    BUILD.mkdir(exist_ok=True)
    intro = card("intro", [("Valtec Technical Test", 64, FG), ("Simulated drone control API — acceptance demo", 34, ACCENT),
                           ("ArduPilot Quad SITL · MAVLink-router · FastAPI · QGroundControl", 26, MUTED),
                           ("Waiting time is sped up; controls are shown live", 22, MUTED)])
    outro = card("outro", [("Acceptance complete", 60, FG), ("QGroundControl and the API controlled the same simulated vehicle", 30, ACCENT),
                           ("through MAVLink-router", 30, ACCENT),
                           ("POST /takeoff  ·  POST /land  ·  POST /goto  ·  POST /rtl  ·  GET /status", 28, FG),
                           ("Final state: landed, armed: false, QGroundControl Ready", 26, MUTED)])
    caps = [caption(i, t, dtl, s) for i, (a, b, s, t, dtl) in enumerate(SEGMENTS)]

    inputs = ["-loop", "1", "-t", "2.5", "-i", str(intro), "-loop", "1", "-t", "3.5", "-i", str(outro), "-i", str(RAW)]
    for c in caps:
        inputs += ["-loop", "1", "-i", str(c)]
    n = len(SEGMENTS)
    fc = ["[0:v]fps=30,format=yuv420p,setsar=1[intro]", "[1:v]fps=30,format=yuv420p,setsar=1[outro]"]
    for i, (a, b, s, _, _) in enumerate(SEGMENTS):
        fc.append(f"[2:v]trim={a - OFFSET:.3f}:{b - OFFSET:.3f},setpts=(PTS-STARTPTS)/{s},fps=30,"
                  f"pad={W}:{H + BAR}:0:0:color=0x0b1220[v{i}]")
        fc.append(f"[v{i}][{3 + i}:v]overlay=0:{H}:shortest=1,format=yuv420p,setsar=1[s{i}]")
    chain = "".join(["[intro]"] + [f"[s{i}]" for i in range(n)] + ["[outro]"])
    fc.append(f"{chain}concat=n={n + 2}:v=1:a=0[out]")
    cmd = ["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[out]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)]
    print(" ".join(cmd[:6]), "... (filter graph with", n, "segments)")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
