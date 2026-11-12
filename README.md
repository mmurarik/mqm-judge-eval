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

## The short version

| Step | What was done | What it showed |
|---|---|---|
| 1. Build the judge | An AI judge for English to Spanish, tested against professional reviewers | Cleared about a third of translations. Missed 1 of 36 with a major error. |
| 2. Check the yardstick | Found a second professional review of the same translations | The two human teams agreed only slightly (kappa 0.09 across 4,928 translations). |
| 3. Compare all three | Judge and both reviews on the 66 test translations they share | The judge matched the original reviewers about as well as the second human team did, and cleared no major errors. |
| 4. Name the weakness | Looked at what the judge flagged that reviewers had passed | It flags too much. Safe but cautious, so it saves less reviewer time than it could. |

The most useful finding was how much the human reviewers disagreed with each
other, because that limits how well any judge can be evaluated.

## How reliable is the yardstick?

The same 2024 English to Spanish translations were reviewed a second time by
different professionals for the WMT24 shared task
(https://github.com/wmt-conference/wmt24-news-systems). That makes it possible
to compare two human reviews with each other, and both with the judge.

**Two human reviews of the same 4,928 translations**

| Measure | Result |
|---|---|
| Put the translation in the same group (no errors, minor only, major) | 56% |
| Agreement beyond chance (kappa) | 0.09 (95% range 0.07 to 0.12) |
| Translations the first review marked major that the second marked clean | 31% of 281 |
| Share flagged by the second review's two vendors | 15% and 67% |

Kappa runs from 0 (no better than chance) to 1 (perfect). Below 0.20 is
conventionally called slight agreement (Landis and Koch, 1977).

**Judge and both reviews on the 66 test translations all three covered**

| Pair | Kappa | 95% range |
|---|---|---|
| Original reviewers and AI judge | 0.29 | 0.11 to 0.46 |
| Original reviewers and second review | 0.20 | 0.03 to 0.36 |
| AI judge and second review | 0.13 | -0.02 to 0.28 |

| Of the 22 translations the original reviewers marked major | Cleared as error-free |
|---|---|
| AI judge | 0 |
| Second human review | 5 |

The ranges overlap, so the claim is "about as well as a second human review",
not "better than".

### Three decisions behind the numbers

| Decision | Why |
|---|---|
| Stopped treating one reviewer as ground truth | One of four reviewers flagged 36% of translations, the others 13% to 16%. Two review teams agreed only slightly on the same text. A judge can only look as good as the yardstick it is measured against. |
| Sized the claim to the sample | 36 major-error cases with 1 miss supports "miss rate under about 12%" at 95% confidence (exact binomial). Claiming "under 5%" needs 59 cases with no misses, or 93 with one. |
| Did not pool data that was not comparable | Public ratings for other languages come from different years, vendors and review schemes. Each language is reported on its own. Russian (2022) was dropped because each reviewer rated exactly one text type, so reviewer and text type cannot be separated. |

### Weaknesses

- One language, a small sample, one judge prompt.
- The judge's extra flags could be real catches or nitpicks. This data cannot
  tell which.
- The second review was uneven. One vendor's reviewers flagged most of what
  they saw. Without that vendor, agreement between the two human reviews rises
  to 0.17 (0.13 to 0.21), still slight.
- The two reviews used different schemes (full MQM, and error spans with
  severity only), so this is agreement across schemes, not a standard
  inter-rater check.
- The scripts for this section are not in the repo yet, and the second
  review's data is not redistributed here because its repo states no license.

### What comes next

- Scale to more languages with the 2024 data, where the same translation
  systems were reviewed in eight languages from English, including
  lower-resource ones like Icelandic and Hindi.
- Move from "how often does the judge agree" to "the judge clears
  translations with a guaranteed maximum miss rate", with the sample sized for
  each language.

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
order. The judge step needs an Anthropic API key in `.env`.

## Outputs

The results are in `out/`, so you can read them without rerunning anything.

- [`out/judge_enes.csv`](out/judge_enes.csv): the judge's verdict on each of
  the 108 test translations, with every error it found, its severity, and the
  judge's explanation.
- [`out/sample_enes.csv`](out/sample_enes.csv): the same 108 translations with
  the reviewer's penalty points and group. Join it to the judge file on
  `seg_id`.
- [`out/segments_enes.csv`](out/segments_enes.csv): all 9,330 translations
  with their penalty points, error count and reviewer.

These files are built from Google's WMT24 MQM ratings
(https://github.com/google/wmt-mqm-human-evaluation), which are licensed under
Apache 2.0. The source passages, translations and reviewer ratings are
Google's. The penalty points and the judge's verdicts are this project's.

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
