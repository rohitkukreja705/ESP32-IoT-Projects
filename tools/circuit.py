"""
circuit.py - draws a clean wiring (circuit) diagram for an ESP32 DevKit V1 (30-pin)
and its peripheral modules, from a small spec.

spec = {
  "title": "...",
  "modules": [
     {"name": "DHT11", "sub": "Temp/Humidity", "side": "L",
      "pins": [("VCC", "3V3"), ("DATA", "G4", "10k pull-up on module"), ("GND", "GND")],
      "outer": ["optional text shown on the far side, e.g. relay load terminals"]},
  ],
  "notes": ["text lines printed under the drawing"],
}
Targets: "G<n>" (GPIO n), "5V", "3V3", "GND".
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

# DOIT ESP32 DevKit V1, 30 pins, viewed from the top, USB at the bottom
LEFT = ["EN", "VP/36", "VN/39", "D34", "D35", "D32", "D33", "D25", "D26", "D27", "D14", "D12", "D13", "GND", "VIN"]
RIGHT = ["D23", "D22", "TX0", "RX0", "D21", "D19", "D18", "D5", "TX2/17", "RX2/16", "D4", "D2", "D15", "GND", "3V3"]
GPIO_LABEL = {36: "VP/36", 39: "VN/39", 1: "TX0", 3: "RX0", 17: "TX2/17", 16: "RX2/16"}

SIGNAL_COLORS = ["#1d4ed8", "#047857", "#7c3aed", "#b45309", "#0e7490", "#be185d",
                 "#4d7c0f", "#9333ea", "#0369a1", "#c2410c", "#15803d", "#6d28d9"]
POWER = {"5V": "#dc2626", "3V3": "#ea580c", "GND": "#111827"}

W, H = 16.0, 11.4
BX0, BX1 = 6.7, 9.3          # board x extent
BTOP = 9.15
PITCH = 0.5
RAIL5, RAIL3, RAILG = 10.75, 10.35, 0.35


def board_pin_xy(label):
    if label in LEFT:
        return BX0, BTOP - 0.55 - LEFT.index(label) * PITCH, "L"
    return BX1, BTOP - 0.55 - RIGHT.index(label) * PITCH, "R"


def gpio_to_label(t):
    n = int(t[1:])
    return GPIO_LABEL.get(n, f"D{n}")


def draw(spec, out_png, dpi=170):
    n_notes = sum(1 for m in spec["modules"] for p in m["pins"] if len(p) > 2 and p[2]) + len(spec.get("notes", []))
    extra = 0.32 * n_notes + 0.35
    fig = plt.figure(figsize=(W, H + extra))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(-extra, H)
    ax.axis("off")

    # ---- rails
    for y, name, txt in [(RAIL5, "5V", "5 V rail  (ESP32 VIN = USB 5 V)"),
                         (RAIL3, "3V3", "3.3 V rail  (ESP32 3V3 pin, max ~500 mA)"),
                         (RAILG, "GND", "GND rail  (common ground)")]:
        ax.plot([0.25, W - 0.25], [y, y], color=POWER[name], lw=3.2, solid_capstyle="round", zorder=1)
        ax.text(0.3, y + 0.09, txt, fontsize=8.5, color=POWER[name], va="bottom", fontweight="bold")

    # ---- ESP32 board
    ax.add_patch(FancyBboxPatch((BX0, 1.15), BX1 - BX0, BTOP - 1.15, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc="#0f3d3a", ec="#0b2b29", lw=2, zorder=3))
    ax.add_patch(Rectangle((BX0 + 0.55, BTOP - 2.3), BX1 - BX0 - 1.1, 1.75, fc="#c9ced3", ec="#8a9096", lw=1, zorder=4))
    ax.text((BX0 + BX1) / 2, BTOP - 1.42, "ESP-WROOM-32", ha="center", va="center", fontsize=8, zorder=5)
    ax.text((BX0 + BX1) / 2, 4.9, "ESP32\nDevKit V1\n(30-pin)", ha="center", va="center", color="white",
            fontsize=11, fontweight="bold", zorder=5, linespacing=1.3)
    ax.add_patch(Rectangle(((BX0 + BX1) / 2 - 0.35, 1.0), 0.7, 0.35, fc="#9ca3af", ec="#6b7280", zorder=4))
    ax.text((BX0 + BX1) / 2, 0.82, "micro-USB", ha="center", fontsize=7, color="#374151")
    for side, pins in (("L", LEFT), ("R", RIGHT)):
        for p in pins:
            x, y, _ = board_pin_xy(p)
            ax.add_patch(Rectangle((x - 0.07, y - 0.07), 0.14, 0.14, fc="#e5c46b", ec="#8a6d1f", zorder=6))
            ax.text(x + (0.14 if side == "L" else -0.14), y, p, fontsize=7.2, color="white",
                    ha="left" if side == "L" else "right", va="center", zorder=6, family="DejaVu Sans Mono")

    # board power pins to rails (dedicated channels right next to the board)
    def power_link(pin, rail, color, chx):
        x, y, s = board_pin_xy(pin)
        ax.plot([x, chx, chx], [y, y, rail], color=color, lw=1.8, zorder=2)
        ax.plot(chx, rail, "o", color=color, ms=4.5, zorder=7)
    power_link("VIN", RAIL5, POWER["5V"], BX0 - 0.18)
    power_link("GND", RAILG, POWER["GND"], BX0 - 0.32)
    power_link("3V3", RAIL3, POWER["3V3"], BX1 + 0.18)
    xg = BX1
    yg = BTOP - 0.55 - RIGHT.index("GND") * PITCH
    ax.plot([xg, BX1 + 0.32, BX1 + 0.32], [yg, yg, RAILG], color=POWER["GND"], lw=1.8, zorder=2)
    ax.plot(BX1 + 0.32, RAILG, "o", color=POWER["GND"], ms=4.5, zorder=7)

    # ---- modules
    def auto_side(m):
        if m.get("side") in ("L", "R") and m.get("force"):
            return m["side"]
        sides = [board_pin_xy(gpio_to_label(p[1]))[2] for p in m["pins"] if p[1] not in POWER]
        if not sides:
            return m.get("side", "L")
        return "L" if sides.count("L") >= sides.count("R") else "R"
    for m in spec["modules"]:
        m["side"] = auto_side(m)
    mods = {"L": [m for m in spec["modules"] if m["side"] == "L"],
            "R": [m for m in spec["modules"] if m["side"] == "R"]}
    color_i = 0
    note_marks = []
    for side in ("L", "R"):
        ms = mods[side]
        if not ms:
            continue
        avail = (RAIL3 - 0.45) - (RAILG + 0.45)
        pp, hdr = 0.42, 0.75 + 0.12                       # pin pitch, header height
        npins = sum(len(m["pins"]) for m in ms)
        need = len(ms) * hdr + npins * pp + (len(ms) + 1) * 0.25
        if need > avail:                                  # compress to fit between the rails
            pp = max(0.3, (avail - (len(ms) + 1) * 0.2 - len(ms) * hdr) / npins)
        heights = [hdr + len(m["pins"]) * pp for m in ms]
        gap = max(0.15, (avail - sum(heights)) / (len(ms) + 1))
        y = RAIL3 - 0.45 - gap
        # channel x positions for this side
        n_wires = sum(len(m["pins"]) for m in ms)
        if side == "L":
            mx0, mx1 = 0.55, 3.55
            chans = [3.85 + i * (BX0 - 0.55 - 3.85) / max(1, n_wires - 1) for i in range(n_wires)]
        else:
            mx0, mx1 = 12.45, 15.45
            chans = [12.15 - i * (12.15 - (BX1 + 0.55)) / max(1, n_wires - 1) for i in range(n_wires)]
        # power wires take the channels nearest the modules, signal wires the
        # channels nearest the board; this keeps most crossings out of the way
        n_pw = sum(1 for m in ms for p in m["pins"] if p[1] in POWER)
        pw_ch, sig_ch = chans[:n_pw], chans[n_pw:]
        # signals: the topmost module pin uses the channel farthest from the board
        pw_i, sig_i = 0, 0
        ci = 0
        for m, h in zip(ms, heights):
            top = y
            ax.add_patch(FancyBboxPatch((mx0, top - h), mx1 - mx0, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                        fc="#eef6f4", ec="#0f766e", lw=1.6, zorder=3))
            ax.text((mx0 + mx1) / 2, top - 0.25, m["name"], ha="center", va="center", fontsize=10.5,
                    fontweight="bold", color="#0b3b37", zorder=5)
            if m.get("sub"):
                ax.text((mx0 + mx1) / 2, top - 0.52, m["sub"], ha="center", va="center", fontsize=7.6,
                        color="#3f5a55", zorder=5)
            for k, pin in enumerate(m["pins"]):
                plabel, target = pin[0], pin[1]
                note = pin[2] if len(pin) > 2 else None
                py = top - 0.85 - k * pp
                px = mx1 if side == "L" else mx0
                ax.add_patch(Rectangle((px - 0.06, py - 0.06), 0.12, 0.12, fc="#e5c46b", ec="#8a6d1f", zorder=6))
                ax.text(px + (-0.13 if side == "L" else 0.13), py, plabel, ha="right" if side == "L" else "left",
                        va="center", fontsize=7.8, family="DejaVu Sans Mono", zorder=6)
                ci += 1
                if target in POWER:
                    chx = pw_ch[pw_i]; pw_i += 1
                else:
                    chx = sig_ch[sig_i]; sig_i += 1
                if target in POWER:
                    col = POWER[target]
                    rail = {"5V": RAIL5, "3V3": RAIL3, "GND": RAILG}[target]
                    ax.plot([px, chx, chx], [py, py, rail], color=col, lw=1.6, zorder=2)
                    ax.plot(chx, rail, "o", color=col, ms=4, zorder=7)
                else:
                    col = SIGNAL_COLORS[color_i % len(SIGNAL_COLORS)]; color_i += 1
                    blabel = gpio_to_label(target)
                    bx, by, bside = board_pin_xy(blabel)
                    if bside == side:
                        ax.plot([px, chx, chx, bx], [py, py, by, by], color=col, lw=1.7, zorder=2)
                    else:  # go under the board to the other side
                        under = 1.0 - 0.09 * (ci % 6)
                        other = BX1 + 0.45 if side == "L" else BX0 - 0.45
                        ax.plot([px, chx, chx, other, other, bx], [py, py, under, under, by, by],
                                color=col, lw=1.7, zorder=2)
                    ax.text(chx + (0.05 if side == "L" else -0.05), by + 0.06 if bside == side else py + 0.06,
                            f"GPIO{target[1:]}", fontsize=6.6, color=col,
                            ha="left" if side == "L" else "right", va="bottom", zorder=8,
                            bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.85))
                if note:
                    note_marks.append(note)
                    idx = len(note_marks)
                    nx = (px + chx) / 2
                    ax.text(nx, py + 0.05, f"[{idx}]", fontsize=7.2, color="#b91c1c", ha="center", va="bottom",
                            fontweight="bold", zorder=8, bbox=dict(fc="white", ec="none", pad=0.3))
            for j, o in enumerate(m.get("outer", [])):
                ox = mx0 + 0.12 if side == "L" else mx1 - 0.12
                ax.text((mx0 + mx1) / 2, top - h + 0.18 + j * 0.24, o, fontsize=6.8, color="#7c2d12",
                        ha="center", va="bottom", style="italic", zorder=6)
            y = top - h - gap

    # ---- title + notes
    ax.text(W / 2, H - 0.22, spec["title"], ha="center", va="top", fontsize=14, fontweight="bold", color="#0b3b37")
    ny = -0.05
    for i, n in enumerate(note_marks):
        ax.text(0.4, ny - i * 0.32, f"[{i + 1}] {n}", fontsize=8.6, color="#7f1d1d", va="top")
    base = ny - len(note_marks) * 0.32
    for j, n in enumerate(spec.get("notes", [])):
        ax.text(0.4, base - j * 0.32, "• " + n, fontsize=8.6, color="#1f2937", va="top")
    fig.savefig(out_png, dpi=dpi, facecolor="white")
    plt.close(fig)
