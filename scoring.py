"""Plain-code rules: mandatory gate, scoring, ranking. No AI in this file."""

def gate(facts, suspicious, criteria):
    """Return (status, reason). status: ok | ineligible | flagged."""
    if suspicious:
        return "flagged", "Contains text aimed at automated reviewers; ignored and sent to a human."
    for key, label in [("licence_held", "Ontario electrical licence"),
                       ("wsib_clearance", "WSIB clearance"),
                       ("liability_insurance_5m", "$5M liability insurance")]:
        v = facts.get(key)
        if v is False:
            return "ineligible", f"Fails mandatory check: {label} not held/stated by the bidder."
        if v is None:
            return "flagged", f"Mandatory check unclear: {label} not found. Needs a human."
    price = facts.get("total_price_cad")
    if price is not None and price > criteria["budget_ceiling_cad"]:
        return "ineligible", "Price is over the budget ceiling."
    weeks = facts.get("completion_weeks")
    if weeks is not None and weeks > criteria["max_weeks"]:
        return "ineligible", "Completion time is over the maximum allowed."
    return "ok", ""


def score_all(pool, criteria):
    """pool: {id: facts} for every bid that passed the gate (or is flagged).
    Returns {id: {"breakdown": {...}, "total": float, "notes": [...]}}."""
    w, p = criteria["weights"], criteria["params"]
    prices = [f["total_price_cad"] for f in pool.values() if f.get("total_price_cad")]
    times = [f["completion_weeks"] for f in pool.values() if f.get("completion_weeks")]
    best_price, best_time = (min(prices) if prices else None), (min(times) if times else None)

    out = {}
    for pid, f in pool.items():
        notes = []
        # Experience: installs / cap
        n = f.get("qualifying_installs_count") or 0
        exp = min(n / p["experience_cap"], 1)
        start = f.get("install_period_start_year")
        if start is not None and start < criteria["window_start_year"]:
            notes.append("Experience may include installs older than 5 years; check.")
        # Price: lowest / this
        price = f.get("total_price_cad")
        pr = (best_price / price) if price and best_price else 0
        if not price:
            notes.append("No price found.")
        # Timeline: shortest / this, missing = 0
        weeks = f.get("completion_weeks")
        tl = (best_time / weeks) if weeks and best_time else 0
        if not weeks:
            notes.append("No completion time stated: timeline scored 0. Ask the bidder.")
        # Warranty: half panel, half workmanship
        pw = min((f.get("panel_warranty_years") or 0) / p["panel_cap_years"], 1)
        ww = min((f.get("workmanship_warranty_years") or 0) / p["workmanship_cap_years"], 1)
        wr = 0.5 * pw + 0.5 * ww
        # Team: 25% each
        team_keys = ["named_project_lead", "crew_described", "safety_plan", "monitoring_plan"]
        tm = sum(0.25 for k in team_keys if f.get(k) is True)

        parts = {"experience": exp, "price": pr, "timeline": tl, "warranty": wr, "team": tm}
        breakdown = {k: round(parts[k] * w[k], 2) for k in parts}
        out[pid] = {"breakdown": breakdown, "total": round(sum(breakdown.values()), 1), "notes": notes}
    return out


def rank(results, statuses):
    """Rank only bids with status 'ranked'. Highest total first; ties broken by letter."""
    ranked = sorted([pid for pid, s in statuses.items() if s == "ranked"],
                    key=lambda pid: (-results[pid]["total"], pid))
    return {pid: i + 1 for i, pid in enumerate(ranked)}
