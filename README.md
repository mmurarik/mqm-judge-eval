# Can an AI review translations like a professional?

A small test of whether an LLM judge finds translation errors the way
professional reviewers do, and where it can and can't be trusted.

## The question

Translation teams check AI-translated content by hand, which is slow and
expensive. Having an AI do the first pass would help, but only if its checks
are reliable. This project measures that on English to Spanish, using expert
reviews as the yardstick.

## Data

Google's public MQM ratings from the WMT 2024 translation evaluation
(https://github.com/google/wmt-mqm-human-evaluation, Apache 2.0). Professional
translators marked every error in machine translations, with a category and a
severity.

## Results

**The AI judge could clear about a third of translations with no human
review, and it let through only 1 of 36 translations with a major error.**

| Finding | Result |
|---|---|
| Translations the judge cleared as error-free | 35% (95% range 22% to 49%) |
| Of those, ones a reviewer had marked with any error | 4.7% |
| Translations with a major error that the judge cleared | 1 of 36 |
| Share of translations each reviewer marked with an error | 36% for one reviewer, 13% to 16% for the other three |

What this means:

- **The judge can take the easy work off reviewers.** Translations it clears
  rarely had errors. Everything else goes to a human.
- **Its one major miss was mechanical.** Leftover web code (`&quot;`) in the
  translation. A plain rule-based check would catch it before the AI sees it.
- **It flags too much.** It marked errors in 21 of 36 translations the
  reviewer had passed. Some are real catches, some are nitpicks. Telling them
  apart needs a third native reviewer. This is the next thing to fix, because
  every false flag costs reviewer time.
- **Reviewers disagree too.** One reviewer flagged far more than the others,
  and was the harshest of the four inside 10 of 14 translation systems, so it
  isn't just that they got worse translations. Any judge measured against a
  single reviewer inherits that reviewer's strictness.

### How the judge and reviewers compared

108 test translations, 36 from each reviewer group (no errors, minor errors
only, a major error). Rows are what the reviewer found; columns are what the
judge found.

| Reviewer found | Judge: no errors | Judge: minor | Judge: major |
|---|---|---|---|
| No errors | 15 | 16 | 5 |
| Minor only | 4 | 25 | 7 |
| Major | 1 | 13 | 22 |

The test used equal groups so each would have enough cases. The 35% figure
reweights them back to their real shares in the data (81% no errors, 13% minor
only, 6% major). The range comes from resampling the 108 translations 5,000
times.

### Limits

- English to Spanish (Mexico) only.
- 108 test translations, each scored by one reviewer.
- One model (Claude Opus 5.5) with one prompt, frozen before the test.
- The judge saw each passage alone; the reviewers saw the surrounding passages.

## How it was done

- **Explore the data** (`src/explore.py`). 11,345 marked errors across 9,330
  translations: 622 English passages, each translated by 15 systems.
- **Score every translation and check the reviewers** (`src/score.py`).
  Penalty points per WMT24: minor 1, minor punctuation 0.1, major 5,
  critical 5, not a translation 25. Then how often each reviewer marked
  errors, overall and inside each system. Overview page:
  [docs/step-2-penalty-scores.html](docs/step-2-penalty-scores.html)
  (download and open in a browser).
- **Pick the test set** (`src/sample.py`). 108 translations, 9 per reviewer
  per group.
- **Run the AI judge** (`src/judge.py`). Prompt frozen at v4, model pinned,
  answers cached.
- **Compare** (`src/compare.py`). The table above, the reweighted clear rate,
  and the range.

To reproduce: `src/get_data.py` downloads the ratings, then run the steps in
order. Step 5 needs an Anthropic API key in `.env`.

## Ideas for later

- **Rule-based checks before the AI.** A plain script that catches mechanical
  failures (web code like `&quot;`, chatbot replies instead of translations,
  text left in English, empty output) on all translations for free, so the AI
  judge only handles meaning. Measure it against the reviewers like the judge.
- **A panel of AI judges.** Several judges review each passage and their answers
  are combined, the way a human panel's would be. One version shapes each judge
  on a real reviewer's style (one strict, others lenient) and checks whether the
  panel beats a single judge.
- **A development set.** Tune the judge's instructions on passages outside the
  test set, then freeze them before the test.
- **Context.** Give the judge the neighboring passages, as the human reviewers had.
- **Other language pairs.** Google's 2024 release covers more than English to
  Spanish; check whether the results hold.
