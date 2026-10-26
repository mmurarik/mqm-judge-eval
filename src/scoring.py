"""MQM scoring: turn a list of errors into one penalty per translation.

0 means perfect. Higher means worse. Used for both the human reviewers and,
later, the AI judge, so the two are scored the same way.
"""
import pandas as pd

# Weights from the dataset's README (Google's MQM documentation).
MINOR = 1.0
MINOR_PUNCTUATION = 0.1   # cosmetic: doesn't change meaning
MAJOR = 5.0
NON_TRANSLATION = 25.0    # the whole segment is unusable

# OUR DECISION: the 2024 data has a "critical" severity the README doesn't weight.
# We chose twice a major error. Changing it changes the system rankings.
CRITICAL = 10.0


def error_weight(category: str, severity: str) -> float:
    """Points for one error."""
    category, severity = category.lower(), severity.lower()
    if "non-translation" in category:
        return NON_TRANSLATION
    if severity == "critical":
        return CRITICAL
    if severity == "major":
        return MAJOR
    if severity == "minor":
        return MINOR_PUNCTUATION if "punctuation" in category else MINOR
    return 0.0  # neutral and no-error


def score_segments(errors: pd.DataFrame) -> pd.DataFrame:
    """One row per translation: its reviewer, text, and total penalty."""
    e = errors.copy()
    e["points"] = [error_weight(c, s) for c, s in zip(e["category"], e["severity"])]
    e["is_major"] = e["severity"].str.lower().isin(["major", "critical"])
    e["is_error"] = e["points"] > 0
    return e.groupby(["system", "globalSegId"], as_index=False).agg(
        rater=("rater", "first"),
        doc=("doc", "first"),
        source=("source", "first"),
        target=("target", "first"),
        penalty=("points", "sum"),
        n_errors=("is_error", "sum"),
        n_major=("is_major", "sum"),
    )
