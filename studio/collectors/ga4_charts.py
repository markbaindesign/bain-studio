#!/usr/bin/env python3
"""
GA4 report charts.
Reads the JSON written by ga4_report.py and draws PNG charts for the /ga-report
skill to embed in the markdown report (and so in the brand-doc PDF).

Usage:
    python3 ga4_charts.py data.json /path/to/report/charts

Writes:
    trend.png      Daily sessions (7-day average), this period vs the previous one
    channels.png   Sessions by channel
    countries.png  Sessions by country (top 8)

Charts are sized to brand-doc's A4 text width (174 x 60 mm) on white, the colour
of its body pages (paper is only used on the cover), so they sit flush on the page. The markdown tables beside them stay in the report
as the accessible table view.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

FONTS = Path(__file__).resolve().parent.parent / "tools/brand-doc/assets/fonts"

# brand-doc palette (brand_doc.py) plus one data colour, validated against SURFACE
SURFACE = "#FFFFFF"
INK = "#141413"
GRAPHITE = "#3D3D3A"
PENCIL = "#8C8A85"
RULE_SOFT = "#D8D0C0"
DATA = "#2a78d6"

SIZE_IN = (174 / 25.4, 60 / 25.4)
DPI = 220


def setup_fonts():
    family = "DejaVu Sans"
    for name in ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Medium.ttf"):
        path = FONTS / name
        if path.exists():
            if hasattr(font_manager.fontManager, "addfont"):
                font_manager.fontManager.addfont(str(path))
            else:  # matplotlib < 3.2
                font_manager.fontManager.ttflist.extend(font_manager.createFontList([str(path)]))
            family = "JetBrains Mono"
    plt.rcParams.update({
        "font.family": family,
        "font.size": 7,
        "text.color": INK,
        "axes.labelcolor": GRAPHITE,
        "xtick.color": GRAPHITE,
        "ytick.color": GRAPHITE,
        "axes.edgecolor": RULE_SOFT,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
    })


def new_axes():
    fig, ax = plt.subplots(figsize=SIZE_IN, dpi=DPI)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    return fig, ax


def save(fig, path):
    fig.tight_layout(pad=0.6)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def rolling(values, window=7):
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1): i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def trend_chart(data, path):
    cur = data["trend"]["current"]
    prev = data["trend"]["previous"]
    if not cur:
        return False
    days = [datetime.strptime(r["date"], "%Y%m%d") for r in cur]
    cur_avg = rolling([int(r["sessions"]) for r in cur])
    prev_avg = rolling([int(r["sessions"]) for r in prev])[: len(cur_avg)]

    fig, ax = new_axes()
    ax.grid(axis="y", color=RULE_SOFT, linewidth=0.6)
    ax.set_axisbelow(True)
    # previous period is context: grey, drawn first so this period sits on top
    ax.plot(days[: len(prev_avg)], prev_avg, color=PENCIL, linewidth=1.1, label="Previous period (aligned by day)")
    ax.plot(days, cur_avg, color=DATA, linewidth=1.6, label="This period")
    for series, colour, label in ((cur_avg, DATA, "This period"), (prev_avg, PENCIL, "Previous")):
        if series:
            ax.annotate(label, (days[len(series) - 1], series[-1]), xytext=(4, 0),
                        textcoords="offset points", va="center", color=GRAPHITE, fontsize=6.5)
    ax.set_ylim(bottom=0)
    ax.set_xlim(days[0], days[-1])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: matplotlib.dates.num2date(x).strftime("%-d %b")))
    ax.set_ylabel("Sessions per day (7-day avg)")
    ax.legend(loc="lower left", frameon=False, fontsize=6.5, ncol=2)
    fig.subplots_adjust(right=0.88)
    save(fig, path)
    return True


def share(v, total):
    pct = v / total
    return "<1%" if 0 < pct < 0.005 else f"{pct:.0%}"


def bar_chart(rows, label_key, path, title_total):
    rows = [r for r in rows if int(r["sessions"]) > 0]
    rows.sort(key=lambda r: int(r["sessions"]))
    labels = [r[label_key] for r in rows]
    values = [int(r["sessions"]) for r in rows]
    total = title_total or sum(values)

    fig, ax = new_axes()
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    bars = ax.barh(labels, values, height=0.72, color=DATA, edgecolor=SURFACE, linewidth=1)
    top = max(values)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + top * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v:,}  ({share(v, total)})", va="center", color=GRAPHITE, fontsize=6.5)
    ax.set_xlim(0, top * 1.22)
    ax.tick_params(axis="y", labelcolor=INK)
    save(fig, path)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: ga4_charts.py data.json OUT_DIR")
    data = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    setup_fonts()

    total = int(data["current"].get("sessions", 0)) or None
    written = []
    if data.get("trend") and trend_chart(data, out / "trend.png"):
        written.append("trend.png")
    if data.get("channels"):
        bar_chart(data["channels"], "sessionDefaultChannelGroup", out / "channels.png", total)
        written.append("channels.png")
    if data.get("countries"):
        bar_chart(data["countries"], "country", out / "countries.png", total)
        written.append("countries.png")
    print("\n".join(str(out / w) for w in written))


if __name__ == "__main__":
    main()
