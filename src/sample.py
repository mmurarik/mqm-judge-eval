"""Step 4: pick a fair, affordable set of segments to test the judge on.

Run from the repo root:  python3 src/sample.py
Reads out/segments_enes.csv (from score.py), writes out/sample_enes.csv.

Why not a random sample: about three quarters of segments have no errors, so
a random draw would mostly test whether the judge leaves clean text alone.
Instead we take the same number from three groups (strata), and spread each
group evenly across the four reviewers.
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "out"
PER_STRATUM = 36          # 36 x 3 groups = 108 segments, 9 per reviewer per group
SEED = 20261025           # fixed, so the same sample comes out every time


def stratum(row) -> str:
    if row["n_major"] > 0:
        return "major"    # at least one major or critical error
    if row["penalty"] > 0:
        return "minor"    # only minor errors
    return "clean"


def main() -> None:
    segs = pd.read_csv(OUT / "segments_enes.csv")
    segs = segs[segs["system"] != "MSLC"]           # broken system; would swamp results
    segs = segs[segs["system"] != "refA"]           # human translation; keep the test to machine output
    segs["stratum"] = segs.apply(stratum, axis=1)

    raters = sorted(segs["rater"].unique())
    per_cell = PER_STRATUM // len(raters)
    picks = []
    for name, group in segs.groupby(["stratum", "rater"]):
        picks.append(group.sample(n=min(per_cell, len(group)), random_state=SEED))
    sample = pd.concat(picks).reset_index(drop=True)

    # Each group's real share of all segments. Needed later to turn sample
    # results back into an estimate for the whole data (the "reweighting").
    share = segs["stratum"].value_counts(normalize=True)
    sample["stratum_share"] = sample["stratum"].map(share)
    sample["seg_id"] = sample["system"] + "|" + sample["globalSegId"].astype(str)
    sample.to_csv(OUT / "sample_enes.csv", index=False)

    print(f"sample size: {len(sample)}")
    print("\nsegments per group and reviewer:")
    print(pd.crosstab(sample["stratum"], sample["rater"]).to_string())
    print("\nreal share of each group in the full data:")
    print((share * 100).round(1).to_string())
    print(f"\nsystems covered: {sample['system'].nunique()}")


if __name__ == "__main__":
    main()
