"""Step 5: ask Claude to find translation errors the way MQM reviewers do.

Run from the repo root:  python3 src/judge.py            (all 108 segments)
                         python3 src/judge.py --limit 3  (a cheap first look)

Needs an Anthropic API key, either exported in your terminal as
ANTHROPIC_API_KEY or saved in a .env file at the repo root (never committed).

Every answer is saved to out/judge_cache/, so re-running costs nothing and
gives identical results. Writes out/judge_enes.csv: one row per segment.
"""
import argparse
import hashlib
import json
import os
import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import anthropic
import pandas as pd

from explore import load
from scoring import error_weight

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
CACHE = OUT / "judge_cache"

MODEL = "claude-opus-5-5"   # pinned: results can't change because the model changed
EFFORT = "medium"           # how hard the model thinks; this model can't turn thinking off
PROMPT_VERSION = "v4"       # bump when the prompt changes, so old cached answers aren't reused
MAX_RETRIES = 8             # retry the same model on busy or failed requests; never switch models
MAX_TOKENS = 8000           # cap on one answer, thinking included; a real answer needs far less
WORKERS = 4                 # requests at once; saves time, not money
CONTEXT = 5                 # neighboring segments shown on each side; reviewers saw up to ten in all

# Spending guard. Prices are Claude Opus 5.5 list prices, $ per million tokens.
BUDGET_USD = 5.00           # total for this project, across every run, counted from the saved answers
PRICE_IN, PRICE_OUT = 4.00, 20.00
WORST_CASE_USD = (8000 * PRICE_IN + MAX_TOKENS * PRICE_OUT) / 1e6  # one request, at most

# Every category the human reviewers used in the 2024 English to Spanish file
# (except source_issue, which is about the English), so the two are comparable.
CATEGORIES = [
    "mistranslation", "addition", "omission", "untranslated", "mt_hallucination",
    "do_not_translate", "wrong_named_entity",
    "grammar", "agreement", "word_order", "spelling", "capitalization", "punctuation",
    "whitespace", "register", "inconsistency", "unnatural_flow", "lacks_creativity",
    "wrong_term", "wrong_language_variety", "number_format", "date_time_format",
    "measurement_format", "non-translation",
]

# Adapted from Google's MQM annotator guidelines (Freitag et al. 2021, Tables 10-12:
# https://arxiv.org/abs/2104.14478). The 2024 English to Spanish ratings were made by
# Unbabel's reviewers under Unbabel's Typology 3.0 (WMT24 metrics report, section 3.2:
# https://aclanthology.org/2024.wmt-1.2), whose full text is behind a login. So the
# critical definition follows Unbabel's public description, and the categories that are
# not in the 2021 guidelines use our own wording.
SYSTEM = """You are a professional English to Spanish translation reviewer. The target is Latin American Spanish, as used in Mexico. You annotate errors using MQM (Multidimensional Quality Metrics), following the guidelines below.

TASK
You will see one English source segment and its Spanish translation. A segment may contain one or more sentences. Identify all errors in the translation. If a translation could be acceptable, it is not an error: a different but correct translation is not an error, and neither is a matter of preference or style.

You are told what kind of text the segment comes from: a news article, a social media post, a literary text, or speech. For speech, the English is an automatic transcript of a video's audio, so it may contain transcription slips. Judge register and style against that kind of text.

You may also see neighboring segments from the same document, in English and Spanish. They are there for context only: mark errors only in the segment under review. Pay attention to document context. If a translation might be questionable on its own but is fine in the context of the document, it is not an error; if it might be acceptable in some context but not within this document, mark it. When no neighboring segments are shown, the segment is the whole document.

HOW TO MARK ERRORS
- Be as fine-grained as possible. If two words are each mistranslated, record two separate mistranslation errors.
- If one stretch of text has several errors, record only the most severe. If they are equally severe, choose the category that comes first in the list below.
- If the translation is so garbled, or so unrelated to the source, that you cannot reliably identify distinct errors, record a single non-translation error covering the whole segment, and no other errors.
- If the translation has no errors, return an empty list.

For each error give:
- span: the exact words in the translation that are wrong (empty if something is missing)
- category: one of the categories below
- severity: minor, major, or critical
- note: a few words on why

SEVERITY
- major: errors that may confuse or mislead the reader due to a significant change in meaning, or because they appear in a visible or important part of the content.
- minor: errors that don't lead to loss of meaning and wouldn't confuse or mislead the reader, but would be noticed, would decrease stylistic quality, fluency or clarity, or would make the content less appealing.
- critical: errors that make the translation unusable or lead to harmful outcomes: health, safety, legal, or financial consequences, or content that could be seen as offensive.
Punctuation that only affects appearance (the kind of quotation mark, spacing around punctuation) is minor. Punctuation that changes the meaning or makes the sentence ungrammatical is major.

CATEGORIES
Accuracy
- mistranslation: the translation does not accurately represent the source.
- addition: the translation includes information not present in the source.
- omission: the translation is missing content from the source.
- untranslated: source text has been left untranslated.
- mt_hallucination: the translation contains content unrelated to the source, as if invented.
- do_not_translate: something that should stay as written (a brand, product name, or code) was translated.
- wrong_named_entity: a name of a person, place, or organization is wrong.
Fluency
- grammar: problems with grammar, other than spelling.
- agreement: words don't agree in gender, number, or person.
- word_order: words are in an incorrect or unnatural order.
- spelling: incorrect spelling.
- capitalization: incorrect capitalization.
- punctuation: incorrect punctuation for the locale or style.
- whitespace: missing or extra spaces.
- register: wrong grammatical register, such as inappropriately informal pronouns.
- inconsistency: internal inconsistency, not related to terminology.
- unnatural_flow: the translation is awkward or reads unnaturally.
- lacks_creativity: the translation is too literal where the source is figurative, idiomatic, or creative.
Terminology
- wrong_term: terminology is non-standard or does not fit the context.
Locale
- wrong_language_variety: the Spanish uses a regional variety that doesn't fit Mexico, or mixes varieties. Vocabulary, pronouns (such as vosotros), or verb habits typical of Spain rather than Mexico belong here.
- number_format, date_time_format, measurement_format: wrong format for numbers, dates and times, or units.
Special
- non-translation: too garbled, or too unrelated to the source, to reliably identify individual errors; covers the whole segment."""

# The reviewers knew what kind of text each passage came from; the doc name says it.
TEXT_TYPES = {"news": "news article", "social": "social media post",
              "literary": "literary text", "speech": "speech (automatic transcript)"}

SCHEMA = {
    "type": "object",
    "properties": {
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "span": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "severity": {"type": "string", "enum": ["minor", "major", "critical"]},
                    "note": {"type": "string"},
                },
                "required": ["span", "category", "severity", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["errors"],
    "additionalProperties": False,
}


def clean(text: str) -> str:
    """Remove the <v>...</v> marks reviewers left in the data, so the judge can't see them."""
    return re.sub(r"</?v>", "", str(text))


def load_key() -> None:
    """Use ANTHROPIC_API_KEY from the terminal, or from a .env file in the repo root."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
                return
    raise SystemExit("No API key. Add ANTHROPIC_API_KEY=... to a .env file in the repo root.")


def add_context(sample: pd.DataFrame) -> pd.DataFrame:
    """Attach the neighboring segments the reviewer saw: same system, same document."""
    full = load().groupby(["system", "globalSegId"], as_index=False).first()
    full["target"] = full["target"].map(clean)
    docs = {k: g.sort_values("docSegId") for k, g in full.groupby(["system", "doc"])}
    position = full.set_index(["system", "globalSegId"])["docSegId"]

    def context(row) -> str:
        here = position[(row["system"], row["globalSegId"])]
        doc = docs[(row["system"], row["doc"])]
        near = doc[(doc["docSegId"] - here).abs().between(1, CONTEXT)]
        return "\n\n".join(
            f"[{'before' if r.docSegId < here else 'after'}]\nEnglish: {r.source}\nSpanish: {r.target}"
            for r in near.itertuples())

    return sample.assign(context=sample.apply(context, axis=1))


def prepare(row) -> tuple:
    """What the judge sees for one segment, and where its answer is saved."""
    source, target = clean(row["source"]), clean(row["target"])
    text_type = TEXT_TYPES[re.search(r"test-en-([a-z]+)", row["doc"]).group(1)]
    message = f"Text type: {text_type}\n\n"
    if row["context"]:
        message += f"NEIGHBORING SEGMENTS (context only, do not mark):\n\n{row['context']}\n\n"
    message += f"SEGMENT UNDER REVIEW\nEnglish source:\n{source}\n\nSpanish translation:\n{target}"
    key = hashlib.sha256(f"{MODEL}|{EFFORT}|{PROMPT_VERSION}|{message}".encode()).hexdigest()[:16]
    return message, CACHE / f"{key}.json"


def judge_one(client: anthropic.Anthropic, row) -> dict:
    """Judge one segment, using the saved answer if we've already asked."""
    message, path = prepare(row)
    if path.exists():
        # two systems can produce the same text; the saved answer is shared, the id is not
        return {**json.loads(path.read_text()), "seg_id": row["seg_id"], "cached": True}

    request = dict(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": message}],
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    response = client.messages.create(**request)

    # model records who actually answered, so a mixed run would show up
    result = {"seg_id": row["seg_id"], "model": response.model,
              "stop_reason": response.stop_reason, "errors": None,
              "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    if response.stop_reason == "end_turn":
        text = next(b.text for b in response.content if b.type == "text")
        result["errors"] = json.loads(text)["errors"]
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return {**result, "cached": False}


def cost_usd(r: dict) -> float:
    return (r["input_tokens"] * PRICE_IN + r["output_tokens"] * PRICE_OUT) / 1e6


def spent_so_far() -> float:
    """Everything this project has paid for: one saved file per answer ever bought."""
    return sum(cost_usd(json.loads(f.read_text())) for f in CACHE.glob("*.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only judge the first N segments")
    args = parser.parse_args()

    load_key()
    CACHE.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(OUT / "sample_enes.csv")
    if args.limit:
        sample = sample.head(args.limit)
    sample = add_context(sample)

    client = anthropic.Anthropic(max_retries=MAX_RETRIES)
    spent = spent_so_far()
    print(f"already spent on this project: ${spent:.2f} of ${BUDGET_USD:.2f}")

    # Start a request only if, even at its worst case, it and the ones still
    # running can't take total spending past the budget.
    todo = [r for _, r in sample.iterrows()]
    results, pending, stop = [], set(), None
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        while todo or pending:
            while todo and not stop and len(pending) < WORKERS:
                if prepare(todo[0])[1].exists():   # already paid for: free to load
                    results.append(judge_one(client, todo.pop(0)))
                    continue
                if spent + (len(pending) + 1) * WORST_CASE_USD > BUDGET_USD:
                    stop = "budget"
                    break
                pending.add(pool.submit(judge_one, client, todo.pop(0)))
            if not pending:
                break
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for f in done:
                try:
                    r = f.result()
                except anthropic.APIError as e:   # e.g. out of credit: keep what we have
                    stop = stop or f"API error: {e}"
                    continue
                results.append(r)
                if not r["cached"]:
                    spent += cost_usd(r)
    if stop:
        print(f"STOPPED EARLY ({stop}). {len(todo)} segments not started; saved answers are kept.")

    rows = []
    for r in results:
        errs = r["errors"] or []
        rows.append({
            "seg_id": r["seg_id"],
            "model": r["model"],
            "judge_ok": r["errors"] is not None,
            "judge_penalty": sum(error_weight(e["category"], e["severity"]) for e in errs),
            "judge_n_errors": len(errs),
            "judge_n_major": sum(e["severity"] in ("major", "critical") for e in errs),
            "judge_errors": json.dumps(errs, ensure_ascii=False),
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "judge_enes.csv", index=False)

    failed = (~out["judge_ok"]).sum()
    new = [r for r in results if not r["cached"]]
    print(f"judged {len(out)} segments ({len(new)} new, {len(out) - len(new)} from saved answers), "
          f"{failed} without an answer")
    print(f"answered by: {out['model'].value_counts().to_dict()}")
    if new:
        run_cost = sum(cost_usd(r) for r in new)
        print(f"this run: ${run_cost:.2f}, about ${run_cost / len(new):.3f} per segment, "
              f"{sum(r['output_tokens'] for r in new) // len(new)} output tokens per segment")
    print(f"total spent on this project: ${spent:.2f} of ${BUDGET_USD:.2f}")
    for r in results[:3]:
        print("\n", r["seg_id"], json.dumps(r["errors"], ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
