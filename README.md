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

## Status

Work in progress. Results will be added here as each step is done.
