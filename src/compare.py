"""Step 6: how much reviewer work could the judge take off the table?

Run from the repo root:  python3 src/compare.py
Reads out/sample_enes.csv and out/judge_enes.csv. Spends nothing.
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "out"
SEED = 20261025


def judge_group(row) -> str:
    if row["judge_n_major"] > 0:
        return "major"
    return "minor" if row["judge_penalty"] > 0 else "clean"


def offload(df: pd.DataFrame, shares: pd.Series) -> tuple[float, float]:
    """Share of all translations the judge clears, and how many of those had reviewer errors.

    The sample has equal groups, so each group's clear rate is weighted by how
    common that group really is.
    """
    cleared = (df["judge"] == "clean").groupby(df["stratum"]).mean()
    by_group = cleared.reindex(shares.index, fill_value=0) * shares
    total = by_group.sum()
    dirty = by_group.drop("clean").sum()
    return total, dirty / total if total else 0.0


def main() -> None:
    sample = pd.read_csv(OUT / "sample_enes.csv")
    judge = pd.read_csv(OUT / "judge_enes.csv")
    df = sample.merge(judge, on="seg_id")
    df["judge"] = df.apply(judge_group, axis=1)
    shares = sample.groupby("stratum")["stratum_share"].first()

    print("1. REVIEWER GROUP (rows) vs JUDGE GROUP (columns), 108 passages")
    print(pd.crosstab(df["stratum"], df["judge"]).reindex(columns=["clean", "minor", "major"], fill_value=0))

    total, dirty = offload(df, shares)
    print("\n2. REWEIGHTED TO REAL SHARES " + ", ".join(f"{k} {v:.1%}" for k, v in shares.items()))
    print(f"   judge clears:                         {total:.1%} of translations")
    print(f"   of those, reviewer had marked errors: {dirty:.1%}")

    majors = df[df["stratum"] == "major"]
    missed = (majors["judge"] == "clean").sum()
    print(f"   major-error passages the judge cleared: {missed} of {len(majors)}")

    # Resample within each group to see how much the clear rate could move by chance.
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(5000):
        resampled = pd.concat(g.sample(len(g), replace=True, random_state=rng) for _, g in df.groupby("stratum"))
        boots.append(offload(resampled, shares)[0])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"   95% range for the clear rate (bootstrap): {lo:.0%} to {hi:.0%}")


if __name__ == "__main__":
    main()
