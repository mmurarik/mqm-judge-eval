"""Step 1: what's in the human ratings?

Run from the repo root:  python3 src/explore.py

Answers five questions about the data before we measure anything.
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "raw" / "mqm_generalMT2024_enes.tsv"


def load() -> pd.DataFrame:
    """Read the file. Each row is one error a reviewer marked (or one "No-error" row)."""
    df = pd.read_csv(DATA, sep="\t", quoting=3, keep_default_na=False)
    # "canary" rows are attention checks planted in the data, not real translations
    return df[df["doc"] != "canary"].copy()


def main() -> None:
    df = load()
    # A segment is one translated passage from one system: the thing that gets scored
    segments = df.groupby(["system", "globalSegId"])

    print("1. HOW BIG IS IT?")
    print(f"   rows (one per error):  {len(df)}")
    print(f"   segments (translations): {segments.ngroups}")
    print(f"   English passages:        {df['globalSegId'].nunique()}")
    print(f"   systems:                 {df['system'].nunique()}  ->  {', '.join(sorted(df['system'].unique()))}")
    print(f"   reviewers:               {df['rater'].nunique()}")

    print("\n2. HOW COMMON IS EACH SEVERITY? (rows)")
    print(df["severity"].str.lower().value_counts().to_string())

    print("\n3. MOST COMMON ERROR TYPES (real errors only)")
    real = df[df["category"].str.lower() != "no-error"]
    print(real["category"].value_counts().head(10).to_string())

    print("\n4. DID ANY REVIEWER RATE THE SAME TRANSLATION AS ANOTHER?")
    per_seg = segments["rater"].nunique()
    print(f"   translations rated by 1 reviewer:   {(per_seg == 1).sum()}")
    print(f"   translations rated by 2+ reviewers: {(per_seg > 1).sum()}")
    per_passage = df.groupby("globalSegId")["rater"].nunique()
    print(f"   English passages whose translations went to all 4 reviewers: {(per_passage == 4).sum()}")

    print("\n5. WHAT DOES A REAL ERROR LOOK LIKE? (the error is marked <v>like this</v>)")
    short = real[(real["severity"].str.lower() == "major") & (real["source"].str.len() < 120)]
    for _, row in short.head(3).iterrows():
        print(f"\n   [{row['category']}, {row['severity']}]  system: {row['system']}, reviewer: {row['rater']}")
        print(f"   EN: {row['source']}")
        print(f"   ES: {row['target']}")


if __name__ == "__main__":
    main()
