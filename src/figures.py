"""Draw the README figures into docs/assets/, one light and one dark version each.

Reads out/sample_enes.csv and out/judge_enes.csv. The three agreement values in
the yardstick figure come from the two-review comparison described in the
README; that analysis is not in this repo yet, so they are written in below.
"""
import re
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
DPI = 200
WIDTH = 9.0  # inches; shown at 900 px in the README

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  grid="#e1e0d9", axis="#c3c2b7", panel="#f1f0ec",
                  seq=["#86b6ef", "#2a78d6", "#104281"], seq_ink=["#0b0b0b", "#ffffff", "#ffffff"],
                  accent="#2a78d6", mark="#fbe3a3", mark_ink="#0b0b0b"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781",
                 grid="#2c2c2a", axis="#383835", panel="#262624",
                 seq=["#9ec5f4", "#3987e5", "#184f95"], seq_ink=["#0b0b0b", "#ffffff", "#ffffff"],
                 accent="#3987e5", mark="#c98500", mark_ink="#0b0b0b"),
}

plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]

# Agreement (Cohen's kappa, three groups) on the 66 test translations that the
# judge and both human reviews cover, with 95% bootstrap ranges.
AGREEMENT = [
    ("AI judge and\noriginal reviewers", 0.29, 0.11, 0.46),
    ("Second review and\noriginal reviewers", 0.20, 0.03, 0.36),
    ("AI judge and\nsecond review", 0.13, -0.02, 0.28),
]


def new_figure(t, height, title, subtitle):
    fig = plt.figure(figsize=(WIDTH, height), dpi=DPI, facecolor=t["surface"])
    top = 1 - 0.30 / height
    fig.text(0.04, top, title, fontsize=15, fontweight="bold", color=t["ink"], va="top")
    fig.text(0.04, top - 0.34 / height, subtitle, fontsize=10.5, color=t["ink2"], va="top")
    return fig


def save(fig, name, theme):
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / f"{name}-{theme}.png", facecolor=fig.get_facecolor())
    plt.close(fig)


def load():
    sample = pd.read_csv(ROOT / "out" / "sample_enes.csv")
    judge = pd.read_csv(ROOT / "out" / "judge_enes.csv")
    both = sample.merge(judge, on="seg_id")
    both["judge_group"] = "minor"
    both.loc[both["judge_n_errors"] == 0, "judge_group"] = "clean"
    both.loc[both["judge_n_major"] > 0, "judge_group"] = "major"
    return both


# ---------------------------------------------------------------- 1. how the test works
def how_it_works(theme):
    t = THEMES[theme]
    height = 3.6
    fig = new_figure(t, height, "How the test works",
                     "A professional reviewer and the AI judge mark errors in the same translation. "
                     "Then the two verdicts are compared.")
    ax = fig.add_axes([0.03, 0.14, 0.94, 0.56])
    ax.set_xlim(-1, 101), ax.set_ylim(0, 40), ax.axis("off")

    def box(x, y, w, h, head, sub, accent=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                    facecolor=t["panel"], linewidth=1.6 if accent else 0.8,
                                    edgecolor=t["accent"] if accent else t["axis"]))
        ax.text(x + w / 2, y + h * 0.63, head, ha="center", va="center", fontsize=11.5,
                fontweight="bold", color=t["ink"])
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=9.5, color=t["ink2"])

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=t["muted"], lw=1.2, shrinkA=0, shrinkB=0))

    box(0, 14, 19, 12, "English passage", "from WMT24")
    box(25, 14, 21, 12, "Spanish translation", "by a machine system")
    box(53, 25, 23, 12, "Professional reviewer", "marks every error")
    box(53, 3, 23, 12, "AI judge", "marks every error", accent=True)
    box(83, 14, 17, 12, "Compare", "same verdict?")
    arrow(19.6, 20, 24.4, 20)
    arrow(46.6, 22, 52.4, 29)
    arrow(46.6, 18, 52.4, 11)
    arrow(76.6, 29, 82.4, 22)
    arrow(76.6, 11, 82.4, 18)

    fig.text(0.04, 0.07, "Why: if the judge's verdicts hold up, the translations it clears "
             "can skip human review, and reviewers keep the hard ones.",
             fontsize=10, color=t["ink2"], va="center")
    save(fig, "how-it-works", theme)


# ---------------------------------------------------------------- 2. judge versus reviewers
def judge_vs_reviewers(theme, both):
    t = THEMES[theme]
    rows = [("clean", "Reviewer found\nno errors"), ("minor", "Reviewer found\nminor errors only"),
            ("major", "Reviewer found\na major error")]
    cols = [("clean", "No errors"), ("minor", "Minor only"), ("major", "Major")]
    counts = pd.crosstab(both["stratum"], both["judge_group"])

    height = 4.3
    fig = new_figure(t, height, "What the judge said about each group of translations",
                     "108 test translations, 36 from each reviewer group. "
                     "Bars show the judge's verdict on the same translations.")
    ax = fig.add_axes([0.22, 0.10, 0.50, 0.56], facecolor=t["surface"])

    for i, (row, _) in enumerate(rows):
        left = 0
        for k, (col, _) in enumerate(cols):
            n = int(counts.loc[row, col])
            ax.barh(i, n, left=left, height=0.56, color=t["seq"][k], edgecolor=t["surface"], linewidth=2)
            if n >= 3:
                ax.text(left + n / 2, i, str(n), ha="center", va="center", fontsize=11,
                        fontweight="bold", color=t["seq_ink"][k])
            left += n
    ax.set_yticks(range(3), [label for _, label in rows], fontsize=10.5, color=t["ink"])
    ax.invert_yaxis()
    ax.set_xlim(0, 36), ax.set_xticks([])
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)

    # legend, in the judge's verdict order
    x = 0.22
    fig.text(x, 0.725, "Judge found:", fontsize=10, color=t["ink2"], va="center")
    x += 0.115
    for k, (_, label) in enumerate(cols):
        fig.patches.append(plt.Rectangle((x, 0.71), 0.022, 0.032, transform=fig.transFigure,
                                         facecolor=t["seq"][k], edgecolor="none"))
        fig.text(x + 0.030, 0.725, label, fontsize=10, color=t["ink"], va="center")
        x += 0.125

    passed_flagged = int(counts.loc["clean", "minor"] + counts.loc["clean", "major"])
    missed = int(counts.loc["major", "clean"])
    notes = {0: (f"{passed_flagged} of 36 flagged", "The judge marked errors\nthe reviewer did not."),
             2: (f"{missed} of 36 cleared", "The judge missed\none major error.")}
    for i, (head, body) in notes.items():
        y = ax.transData.transform((0, i))[1] / (height * DPI)
        fig.text(0.745, y + 0.035, head, fontsize=11, fontweight="bold", color=t["ink"], va="center")
        fig.text(0.745, y - 0.045, body, fontsize=9.5, color=t["ink2"], va="center", linespacing=1.3)
    save(fig, "judge-vs-reviewers", theme)


# ---------------------------------------------------------------- 3. the yardstick
def yardstick(theme):
    t = THEMES[theme]
    height = 3.9
    fig = new_figure(t, height, "The judge agrees with the reviewers about as well as other reviewers do",
                     "66 test translations reviewed by the judge and by two human review teams. "
                     "Dot: agreement (kappa). Line: 95% range.")
    ax = fig.add_axes([0.25, 0.20, 0.71, 0.48], facecolor=t["surface"])
    ax.set_xlim(-0.08, 1.0), ax.set_ylim(len(AGREEMENT) - 0.5, -0.5)

    bands = [(0.0, 0.2, "slight"), (0.2, 0.4, "fair"), (0.4, 0.6, "moderate"),
             (0.6, 0.8, "substantial"), (0.8, 1.0, "almost perfect")]
    for lo, hi, name in bands:
        ax.axvline(lo, color=t["grid"], lw=1, zorder=0)
        ax.text((lo + hi) / 2, -0.62, name, ha="center", va="bottom", fontsize=9, color=t["muted"])
    ax.axvline(1.0, color=t["grid"], lw=1, zorder=0)
    ax.axvline(0.0, color=t["axis"], lw=1.2, zorder=0)

    for i, (_, k, lo, hi) in enumerate(AGREEMENT):
        ax.plot([lo, hi], [i, i], color=t["accent"], lw=2, solid_capstyle="round", zorder=2)
        ax.plot([k], [i], "o", ms=10, color=t["accent"], markeredgecolor=t["surface"],
                markeredgewidth=2, zorder=3)
        ax.text(hi + 0.025, i, f"{k:.2f}", fontsize=11, fontweight="bold", color=t["ink"], va="center")
        ax.text(hi + 0.095, i, f"({lo:.2f} to {hi:.2f})".replace("-", "−"), fontsize=9.5,
                color=t["ink2"], va="center",
                bbox=dict(facecolor=t["surface"], edgecolor="none", pad=2), zorder=4)
    ax.set_yticks(range(len(AGREEMENT)), [name for name, *_ in AGREEMENT], fontsize=10.5, color=t["ink"])
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], ["0\nchance", "0.2", "0.4", "0.6", "0.8", "1\nperfect"],
                  fontsize=9.5, color=t["ink2"])
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    fig.text(0.04, 0.045, "The ranges overlap, so no pair is clearly ahead. "
             "Band names follow Landis and Koch (1977), a convention.",
             fontsize=9.5, color=t["ink2"], va="center")
    save(fig, "yardstick", theme)


# ---------------------------------------------------------------- 5. the one miss
def one_miss(theme, both):
    t = THEMES[theme]
    cleared = both[(both["stratum"] == "major") & (both["judge_group"] == "clean")]
    assert len(cleared) == 1, "expected exactly one major-error translation cleared by the judge"
    row = cleared.iloc[0]
    source = row["source"]
    target = re.sub(r"</?v>", "", row["target"])
    token = "&quot;"

    height = 5.6
    fig = new_figure(t, height, "The one major error the judge cleared",
                     "Leftover web code for quotation marks. The reviewer flagged it; the judge read past it.")
    ax = fig.add_axes([0, 0, 1, 1])
    w, h = WIDTH * DPI, height * DPI
    ax.set_xlim(0, w), ax.set_ylim(0, h), ax.axis("off")
    renderer = fig.canvas.get_renderer()
    left, line_h = 0.04 * w, 44

    def heading(y, text):
        ax.text(left, y, text, fontsize=8.5, fontweight="bold", color=t["muted"], va="top")

    def paragraph(y, text, marked=False):
        for line in textwrap.wrap(text, 128):
            x = left
            for part in re.split(f"({re.escape(token)})", line):
                if not part:
                    continue
                hit = marked and part == token
                if hit:
                    x += 5
                item = ax.text(x, y, part, fontsize=9.5, va="top", family="Menlo" if hit else None,
                               color=t["mark_ink"] if hit else t["ink"],
                               bbox=dict(facecolor=t["mark"], edgecolor="none", pad=1.5) if hit else None)
                x += item.get_window_extent(renderer).width + (5 if hit else 0)
                if part.endswith(" "):
                    x += ax.text(0, -100, "a a", fontsize=9.5).get_window_extent(renderer).width \
                        - ax.text(0, -100, "aa", fontsize=9.5).get_window_extent(renderer).width
            y -= line_h
        return y

    y = h - 235
    heading(y, "ENGLISH SOURCE")
    y = paragraph(y - 40, source)
    y -= 26
    heading(y, "MACHINE TRANSLATION")
    y = paragraph(y - 40, target, marked=True)

    y -= 30
    box_h, gap = 285, 0.02 * w
    box_w = (w - 2 * left - gap) / 2
    verdicts = [
        ("PROFESSIONAL REVIEWER", "Major error",
         f"Marked the first {token} as critical and\nthree more as minor punctuation.\n"
         f"{row['penalty']:.1f} penalty points.", False),
        ("AI JUDGE", "No errors",
         "Cleared the translation.\nIt found nothing to mark.", True),
    ]
    for i, (who, verdict, detail, accent) in enumerate(verdicts):
        x = left + i * (box_w + gap)
        ax.add_patch(FancyBboxPatch((x, y - box_h), box_w, box_h, boxstyle="round,pad=0,rounding_size=14",
                                    facecolor=t["panel"], linewidth=1.6 if accent else 0.8,
                                    edgecolor=t["accent"] if accent else t["axis"]))
        ax.text(x + 30, y - 30, who, fontsize=8.5, fontweight="bold", color=t["muted"], va="top")
        ax.text(x + 30, y - 72, verdict, fontsize=13, fontweight="bold", color=t["ink"], va="top")
        ax.text(x + 30, y - 128, detail, fontsize=9.5, color=t["ink2"], va="top", linespacing=1.4)

    ax.text(left, 62, f"{token} is web code for a quotation mark that was never converted. "
            "A plain rule-based check would catch it before the judge sees the text.",
            fontsize=9.5, color=t["ink2"], va="center")
    save(fig, "one-miss", theme)


def main():
    both = load()
    for theme in THEMES:
        how_it_works(theme)
        judge_vs_reviewers(theme, both)
        yardstick(theme)
        one_miss(theme, both)
    print(f"wrote {len(list(ASSETS.glob('*.png')))} images to {ASSETS}")


if __name__ == "__main__":
    main()
