"""Tests for the LLM extractor that run without an API key (PydanticAI TestModel)."""
from pydantic_ai.models.test import TestModel

from llm_extract import Extraction, compare, extract_llm, make_agent
from main import Finding, Rating, extract

REPORT = "P-001 | Bodenbelag | Küche 1 | Asbest | 12,5 mg/kg | sanierungsbedürftig\n"


def fake_answer():
    return {"findings": [{"sample_id": "P-001", "component": "Bodenbelag",
                          "room": "Küche 1", "pollutant": "Asbest", "value": 12.5,
                          "unit": "mg/kg", "rating": "sanierungsbedürftig"}]}


def test_llm_extractor_returns_validated_findings():
    agent = make_agent("test")
    with agent.override(model=TestModel(custom_output_args=fake_answer())):
        findings = extract_llm(REPORT, agent)
    assert findings == [Finding(sample_id="P-001", component="Bodenbelag", room="Küche 1",
                                pollutant="Asbest", value=12.5, unit="mg/kg",
                                rating=Rating.REMEDIATE)]


def test_compare_identical_extractions():
    ref = extract(REPORT)
    assert compare(ref, ref) == {"reference": 1, "candidate": 1, "identical": 1,
                                 "different": [], "missing": [], "extra": []}


def test_compare_reports_differences_and_missing():
    ref = extract(REPORT)
    changed = [ref[0].model_copy(update={"value": 99.0})]
    assert compare(ref, changed)["different"] == ["P-001"]
    assert compare(ref, [])["missing"] == ["P-001"]
