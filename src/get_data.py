"""Download the English to Spanish MQM ratings from Google's public repo.

Run from the repo root:  python3 src/get_data.py

The file goes to data/raw/, which git ignores: it's Google's data, so we point
to it instead of copying it into this repo.
"""
from pathlib import Path
from urllib.request import urlretrieve

URL = ("https://raw.githubusercontent.com/google/wmt-mqm-human-evaluation/"
       "main/generalMT2024/mqm_generalMT2024_enes.tsv")
DEST = Path(__file__).resolve().parent.parent / "data" / "raw" / "mqm_generalMT2024_enes.tsv"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        print(f"Already downloaded: {DEST}")
        return
    print("Downloading (about 7 MB)...")
    urlretrieve(URL, DEST)
    print(f"Saved to {DEST}")


if __name__ == "__main__":
    main()
