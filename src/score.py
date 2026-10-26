"""Step 2: score every translation, then look at systems and reviewers.

Run from the repo root:  python3 src/score.py
Saves out/segments_enes.csv (one row per translation).
"""
from pathlib import Path

from explore import load
from scoring import score_segments

OUT = Path(__file__).resolve().parent.parent / "out"


def main() -> None:
    segs = score_segments(load())
    OUT.mkdir(exist_ok=True)
    segs.to_csv(OUT / "segments_enes.csv", index=False)

    print("1. HOW GOOD ARE THE TRANSLATIONS OVERALL?")
    print(f"   perfect (penalty 0):          {(segs['penalty'] == 0).mean():.0%}")
    print(f"   at least one major error:     {(segs['n_major'] > 0).mean():.0%}")
    print(f"   average penalty:              {segs['penalty'].mean():.2f}")

    print("\n2. WHICH SYSTEMS ARE BEST? (average penalty, lower is better; refA is the human translator)")
    ranking = segs.groupby("system")["penalty"].mean().sort_values()
    for rank, (system, penalty) in enumerate(ranking.items(), start=1):
        print(f"   {rank:2}. {system:<18} {penalty:.2f}")

    # MSLC is so broken it would distort the reviewer comparison, so leave it out.
    fair = segs[segs["system"] != "MSLC"]
    print("\n3. ARE SOME REVIEWERS HARSHER? (share of translations each one marked with any error)")
    harsh = (fair["penalty"] > 0).groupby(fair["rater"]).mean()
    for rater, share in harsh.items():
        print(f"   {rater}: {share:.0%}")

    print("\n   Same check within each system, so it's not just who got the worse systems:")
    by_system = (fair.assign(any_error=fair["penalty"] > 0)
                 .pivot_table(index="system", columns="rater", values="any_error", aggfunc="mean"))
    harshest = by_system.idxmax(axis=1).value_counts()
    print(f"   systems where each reviewer was the harshest of the four: {harshest.to_dict()}")


if __name__ == "__main__":
    main()
