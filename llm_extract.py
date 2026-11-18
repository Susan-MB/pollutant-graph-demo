"""LLM-based extraction of findings from a pollutant report (PydanticAI).

Returns the same `Finding` objects as the rule-based parser in main.py, so both
extractors can be compared and the rest of the pipeline stays unchanged.

Usage:
    set ANTHROPIC_API_KEY=...            (or OPENAI_API_KEY=... for an OpenAI model)
    python llm_extract.py report.txt     (default model: see DEFAULT_MODEL)
    python llm_extract.py report.txt openai:gpt-4o
"""
import os
import sys
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent

from main import Finding, Rating, build_graph, extract

DEFAULT_MODEL = os.getenv("LLM_MODEL", "anthropic:claude-sonnet-4-5")

INSTRUCTIONS = f"""You extract findings from German pollutant reports (Schadstoffgutachten).
Return one finding per sample. Rules:
- sample_id: the sample ID exactly as written (e.g. "P-001").
- component: the building component (Bauteil).
- room: the room or location (Raum).
- pollutant: the pollutant name.
- value / unit: the measured amount as a number plus its unit. Use null for both if
  the report gives no number (e.g. "n.n." = not detected).
- rating: exactly one of {[r.value for r in Rating]}. Map the report's wording to the
  closest of these values. If a sample has no clear rating, omit that sample.
Do not invent samples or values that are not in the text."""


class Extraction(BaseModel):
    findings: list[Finding]


def make_agent(model: str | None = None) -> Agent:
    return Agent(model or DEFAULT_MODEL, output_type=Extraction,
                 instructions=INSTRUCTIONS, retries=2)


def extract_llm(text: str, agent: Agent | None = None) -> list[Finding]:
    """Extract findings with an LLM. Output is validated against `Finding`."""
    agent = agent or make_agent()
    return agent.run_sync(text).output.findings


def compare(a: list[Finding], b: list[Finding]) -> dict:
    """Compare two extractions sample by sample (a = reference, b = candidate)."""
    ra = {f.sample_id: f for f in a}
    rb = {f.sample_id: f for f in b}
    same = [k for k in ra if k in rb and ra[k] == rb[k]]
    differ = [k for k in ra if k in rb and ra[k] != rb[k]]
    return {"reference": len(ra), "candidate": len(rb), "identical": len(same),
            "different": sorted(differ),
            "missing": sorted(set(ra) - set(rb)),
            "extra": sorted(set(rb) - set(ra))}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "report.txt"
    model = sys.argv[2] if len(sys.argv) > 2 else None
    text = Path(path).read_text(encoding="utf-8")

    reference = extract(text)                           # rule-based
    candidate = extract_llm(text, make_agent(model))    # LLM

    print(f"rule-based: {len(reference)} findings, LLM: {len(candidate)} findings")
    print("comparison:", compare(reference, candidate))
    print(f"graph from LLM output: {len(build_graph(candidate))} triples")
