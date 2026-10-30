"""AI extraction step (live) and mock loader. The AI only extracts facts."""
import json, os, re, hashlib
from pathlib import Path

HERE = Path(__file__).parent
PROMPTS_MD = HERE.parent / "PROMPTS.md"

INJECTION_PATTERNS = [
    r"automated (review|system)", r"ignore (all |any )?(previous|prior)", r"rank (it|this)[^.]{0,30}first",
    r"full marks", r"pre-?approved", r"note to (ai|automated|reviewer)", r"system prompt",
]


def prescan(text):
    """Rule-based injection pre-scan. Returns list of suspicious snippets."""
    hits = []
    for pat in INJECTION_PATTERNS:
        for m in re.finditer(pat, text, flags=re.I):
            hits.append({"quote": text[max(0, m.start() - 20): m.end() + 40].strip(), "location": "pre-scan"})
    return hits


def load_system_prompt():
    """Use the exact prompt in PROMPTS.md (first code block) so docs and code never drift."""
    md = PROMPTS_MD.read_text()
    block = re.search(r"```\n(You are a data-extraction tool.*?)```", md, flags=re.S).group(1)
    return block, hashlib.sha256(block.encode()).hexdigest()[:12]


def read_text(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return path.read_text()


def flatten(raw):
    """Turn the prompt's nested output into flat values + evidence map."""
    facts, evidence = {}, {}
    for k, v in raw.get("facts", {}).items():
        facts[k] = v.get("value") if v.get("found", True) else None
        evidence[k] = v.get("evidence", "")
    return facts, evidence, raw.get("suspicious_text", [])


def verify_quotes(facts, evidence, text):
    """Rule check: a fact is kept only if its quote really appears in the source text."""
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    src, problems = norm(text), []
    for k, quote in evidence.items():
        if facts.get(k) is not None and quote and norm(quote) not in src:
            facts[k] = None
            problems.append(f"{k}: quote not found in source, value discarded")
    return problems


def live_extract(pid, text, criteria):
    import anthropic
    system, prompt_hash = load_system_prompt()
    system = system.replace("{criteria_version}", criteria["version"]).replace("{criteria_fields_json}", "(see output shape)")
    client = anthropic.Anthropic()
    model = os.environ["MODEL"]
    msg = f"PROPOSAL ID: {pid}\n<proposal>\n{text}\n</proposal>"
    for attempt in range(2):  # one retry on bad JSON, then give up and flag
        try:
            resp = client.messages.create(model=model, max_tokens=2500, temperature=0,
                                          system=system, messages=[{"role": "user", "content": msg}])
        except anthropic.BadRequestError:  # some models reject temperature; retry without
            resp = client.messages.create(model=model, max_tokens=2500,
                                          system=system, messages=[{"role": "user", "content": msg}])
        raw_text = resp.content[0].text.strip()
        try:
            return json.loads(raw_text), model, prompt_hash
        except json.JSONDecodeError:
            continue
    return None, model, prompt_hash


def mock_extract(pid):
    data = json.loads((HERE / "mock_extractions.json").read_text())[pid]
    return data["facts"], data["suspicious_text"]
