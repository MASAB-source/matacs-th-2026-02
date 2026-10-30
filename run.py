"""Run the triage pipeline.
  python run.py --mock                 # no API key needed, uses mock_extractions.json
  python run.py --live --samples DIR   # reads DIR/A.pdf (or .txt), calls the AI
  python run.py --mock --criteria other_criteria.json   # re-score with changed criteria
"""
import argparse, json, hashlib, datetime
from pathlib import Path
import extract, scoring

HERE = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--criteria", default=str(HERE / "criteria.json"))
    args = ap.parse_args()
    if args.live:
        try:
            from dotenv import load_dotenv; load_dotenv()
        except ImportError:
            pass

    criteria = json.loads(Path(args.criteria).read_text())
    audit = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "criteria_version": criteria["version"], "mode": "live" if args.live else "mock", "proposals": {}}

    facts_by, susp_by, problems_by = {}, {}, {}
    ids = sorted(json.loads((HERE / "mock_extractions.json").read_text()).keys()) if args.mock else \
          sorted(p.stem for p in Path(args.samples).iterdir() if p.suffix in (".pdf", ".txt"))

    for pid in ids:
        problems = []
        if args.mock:
            facts, susp = extract.mock_extract(pid)
        else:
            path = next(Path(args.samples).glob(pid + ".*"))
            text = extract.read_text(path)
            audit["proposals"].setdefault(pid, {})["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            raw, model, phash = extract.live_extract(pid, text, criteria)
            audit["model"], audit["prompt_hash"] = model, phash
            if raw is None:
                facts, susp = {}, [{"quote": "AI output was not valid JSON twice", "location": "extraction"}]
            else:
                facts, evidence, susp = extract.flatten(raw)
                problems += extract.verify_quotes(facts, evidence, text)
            susp = susp + extract.prescan(text)
        facts_by[pid], susp_by[pid], problems_by[pid] = facts, susp, problems

    # Mandatory gate
    status, reason = {}, {}
    for pid in ids:
        s, r = scoring.gate(facts_by[pid], susp_by[pid], criteria)
        status[pid] = {"ok": "ranked"}.get(s, s)
        reason[pid] = r

    # Score every bid that is not ineligible (flagged ones get a 'shadow' score for the reviewer only)
    pool = {pid: facts_by[pid] for pid in ids if status[pid] != "ineligible"}
    results = scoring.score_all(pool, criteria)
    ranks = scoring.rank(results, status)

    output = []
    for pid in ids:
        r = results.get(pid)
        entry = {"proposal": pid, "rank": ranks.get(pid), "status": status[pid],
                 "score": r["total"] if r and status[pid] == "ranked" else None,
                 "reason": reason[pid] or "; ".join(r["notes"]) or "Scored on all criteria."}
        if status[pid] == "flagged" and r:
            entry["reason"] += f" (Shadow score ignoring the flag: {r['total']}.)"
        output.append(entry)
        audit["proposals"].setdefault(pid, {}).update(
            {"facts": facts_by[pid], "suspicious_text": susp_by[pid], "quote_problems": problems_by[pid],
             "status": status[pid], "breakdown": r["breakdown"] if r else None, "total": r["total"] if r else None})

    (HERE / "output_ranking.json").write_text(json.dumps(output, indent=2))
    with open(HERE / "audit_log.jsonl", "a") as f:
        f.write(json.dumps(audit) + "\n")

    print(f"Criteria {criteria['version']} | mode: {audit['mode']}\n")
    for e in sorted(output, key=lambda e: (e["rank"] is None, e["rank"] or 0, e["proposal"])):
        print(f"{e['proposal']}  rank={e['rank']}  {e['status']:<10} score={e['score']}  {e['reason'][:90]}")
        if results.get(e["proposal"]):
            print("     breakdown:", results[e["proposal"]]["breakdown"])


if __name__ == "__main__":
    main()
