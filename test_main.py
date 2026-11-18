import logging

import pytest

from main import QUERY, Finding, Rating, build_graph, extract, parse_amount

HEADER = "Probe | Bauteil | Raum | Schadstoff | Menge | Bewertung\n"


def test_parse_amount_decimal_comma():
    assert parse_amount("12,5 mg/kg") == (12.5, "mg/kg")


def test_parse_amount_integer():
    assert parse_amount("450 mg/kg") == (450.0, "mg/kg")


def test_parse_amount_not_detected():
    assert parse_amount("n.n.") == (None, None)


def test_extract_valid_row():
    text = HEADER + "P-001 | Bodenbelag | Küche 1 | Asbest | 12,5 mg/kg | sanierungsbedürftig\n"
    findings = extract(text)
    assert len(findings) == 1
    f = findings[0]
    assert f.sample_id == "P-001"
    assert f.value == 12.5 and f.unit == "mg/kg"
    assert f.rating is Rating.REMEDIATE


def test_extract_ignores_header_and_free_text():
    assert extract(HEADER + "Some free text\n") == []


def test_rating_is_case_insensitive():
    findings = extract("P-005 | Fliesenkleber | Bad | Asbest | 3 mg/kg | Unbedenklich\n")
    assert findings[0].rating is Rating.OK


def test_unknown_rating_is_skipped_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="pollutant-demo"):
        findings = extract("P-007 | Teerkleber | Flur | PAK | 90 mg/kg | unbekannt\n")
    assert findings == []
    assert "line 1 skipped" in caplog.text


def test_wrong_column_count_is_skipped_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="pollutant-demo"):
        findings = extract("P-006 | kaputte Zeile | Flur\n")
    assert findings == []
    assert "expected 6 columns" in caplog.text


def test_graph_handles_special_characters_in_room_names():
    f = Finding(sample_id="P-002", component="Fensterkitt", room="Keller / Nord",
                pollutant="PCB", value=450, unit="mg/kg", rating=Rating.REMEDIATE)
    g = build_graph([f])
    iris = {str(s) for s in g.subjects()}
    assert "https://example.org/room/Keller%20%2F%20Nord" in iris
    assert all(" " not in i for i in iris)


def test_query_excludes_components_flagged_for_remediation():
    findings = [
        Finding(sample_id="P-001", component="Bodenbelag", room="Küche 1",
                pollutant="Asbest", value=12.5, unit="mg/kg", rating=Rating.REMEDIATE),
        Finding(sample_id="P-003", component="Wandfarbe", room="Büro 2",
                pollutant="Blei", value=80, unit="mg/kg", rating=Rating.OK),
    ]
    rows = {(str(r), str(c)) for r, c, _ in build_graph(findings).query(QUERY)}
    assert rows == {("Büro 2", "Wandfarbe")}


@pytest.mark.parametrize("value", [None, 0.0])
def test_missing_or_zero_amount_is_allowed(value):
    f = Finding(sample_id="P-004", component="Dämmung", room="Dachboden",
                pollutant="KMF", value=value, rating=Rating.MONITOR)
    assert f.unit is None
