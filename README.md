# matacs-th-2026-02

# MATACS-TH-2026-02: AI Proposal Triage Design

- **Name:** Masab Bin Wisal
- **Reference:** MATACS-TH-2026-02
- **Time actually spent:** 1 hour

## Files
- [WRITEUP.md](WRITEUP.md): answers to the five questions
- [diagram/process-flow.png](diagram/process-flow.png): flow from upload to ranked output
- [PROMPTS.md](PROMPTS.md): extraction and reason prompts
- [ranking.json](ranking.json): expected ranking of proposals A to E
- prototype folder

## How I used AI tools
I used Claude to draft the design, prompt and prototype. It scored Proposal D’s missing timeline as 0 and still ranked it third. I disagreed because a bid with no schedule can’t be fairly compared, and ranking it hides that gap from the reviewer. I changed the rule so D is flagged for clarification instead, and updated the code, ranking.json and write-up to match.
