# Write-up: AI Proposal Triage (MATACS-TH-2026-02)

**Assumptions:** "Last 5 years" means 2021 onward. Missing information is never guessed. The scoring formulas below are my choice and can be edited by an admin like any other criteria setting.

## 1. AI vs. rules

**AI is used for:** (a) reading messy proposal text and extracting facts with a supporting quote, and (b) optionally phrasing a one-line reason from the finished numbers.

**Plain code is used for:** file handling, loading criteria, the mandatory pass/fail gate, all scoring, ranking, and logging.

I drew the line where judgement about language is needed (AI) versus where the answer is arithmetic that must be identical every time (code). Proposals are written in different styles, so AI helps there. Weights and formulas are set by the admin, so they must not live inside a prompt.

Scoring formulas (weights come from the admin's criteria):
- Experience: qualifying installs / 12, capped at 1.
- Price: lowest eligible price / this price.
- Timeline: shortest eligible time / this time; no time stated = 0.
- Warranty: half panel (years / 25) and half workmanship (years / 12), each capped at 1.
- Team: 25% each for named lead, crew, safety plan, monitoring plan.

## 2. Consistency and explainability

- Temperature 0, fixed model and prompt version, and a strict JSON output.
- Extraction is saved once per proposal and reused, so re-ranking does not re-ask the AI. Re-scoring the same saved facts always gives the same result.
- If the same PDFs were re-uploaded and re-extracted, wording could vary slightly. Quote checks and number-only fields keep this small, and any difference in extracted facts is shown to the reviewer.
- For each proposal the reviewer sees a table: each criterion, the extracted value, the quote from the PDF, the points earned, and the total.

## 3. Human in the loop

- The reviewer checks flagged and ineligible bids, can correct any extracted value (with a required note), and can request bidder clarification. Scores recalculate instantly from the corrected facts.
- The reviewer confirms the ranking. A person makes the final award decision; the tool never awards anything.
- Audit log: who uploaded what, file hashes, criteria version, prompt and model version, raw AI output, every override with user, time and reason, and the final decision.

## 4. Changing criteria

- Criteria are versioned. A saved ranking is tied to the version that produced it and is never silently changed.
- Weights or formula change: re-score from saved facts in code (instant, no AI cost), shown as a new run next to the old one.
- Criteria added or changed: re-extract only the new fields.
- Old rankings show an "outdated criteria" banner. Reviewer overrides carry forward but are re-confirmed. If a decision was already recorded, it stays on record with its original version.

## 5. Risks

| Risk | Safeguard |
|---|---|
| Wrong extraction | Every fact needs a quote that must exist in the source text; reviewer sees quotes; unclear values flagged |
| Made-up facts | "Not stated = null" rule; missing data scores 0 or is flagged, never guessed |
| Manipulation (hidden instructions) | Proposal treated as data only; pre-scan plus AI detection; flagged for a human; instructions never affect scores |
| Bias (for example favouring big or well-written bids) | Scoring is in code on facts only; AI never sees weights or ranks; no use of company name, size or style; periodic spot-checks |
| Unit/currency/date errors | Code validates units and flags unclear ones |
| Bad scans | OCR confidence check; low quality sends the file to the reviewer |
| Cost | One extraction call per proposal, results cached, re-scoring is free |
| Privacy | Fictional/consented data only, no keys in the repo, retention rules |

## Sample results

- **A (98.0, rank 1):** strong on every criterion.
- **E (87.7, rank 2):** best warranty and monitoring, slightly less experience.
- **D (73.8, rank 3):** best price, but no schedule. A clarification could change its rank.
- **B (ineligible):** licence not held by the bidder, even though cheapest and fastest.
- **C (flagged):** hidden instruction to rank it first. Ignored. If cleared by a human it would score about 80, above D. Its "since 2020" experience dates also need checking.
