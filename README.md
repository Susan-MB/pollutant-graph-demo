# Pollutant Graph Demo

A small Python prototype that turns a pollutant report (*Schadstoffgutachten*) into a
knowledge graph and answers questions about it.

```
report  ->  typed findings (Pydantic)  ->  RDF graph (rdflib)  ->  SPARQL queries
              ^ rule-based parser or LLM extractor (PydanticAI)
```

> **Note:** `report.txt` contains **invented sample data**, not a real report. It includes
> two deliberately invalid rows (`P-006`, `P-007`) to show that bad input is reported
> instead of silently ignored.

## Features

- **Typed extraction:** each row becomes a `Finding` (Pydantic). The amount is split into a
  numeric `value` and a `unit` (`"12,5 mg/kg"` -> `12.5`, `"mg/kg"`; `"n.n."` -> missing).
- **Validated ratings:** `Rating` is an enum (matched case-insensitively). Unknown values are
  rejected and logged as warnings.
- **Knowledge graph:** rooms, components and pollutants are separate RDF resources linked by
  `ex:hasComponent` and `ex:contains`. Names are URL-encoded, so `Keller / Nord` gives a valid IRI.
- **SPARQL queries:** components not flagged for remediation (a screening hint, not proof of
  reusability) and rooms containing a given pollutant.
- **LLM extractor (optional):** `llm_extract.py` uses PydanticAI to return the same `Finding`
  objects, and `compare()` checks it against the rule-based parser.
- **Tests:** 15 pytest tests that run offline, without an API key.

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Rule-based extraction, graph building, SPARQL queries |
| `llm_extract.py` | LLM-based extraction (PydanticAI) and comparison with the rule-based parser |
| `test_main.py` | Tests for parsing, validation, graph and query |
| `test_llm_extract.py` | Tests for the LLM extractor using PydanticAI's `TestModel` (no network) |
| `report.txt` | Invented sample report |
| `requirements.txt` | Dependencies |

## Installation

Requires Python 3.10 or newer.

```bash
git clone https://github.com/YOUR-USERNAME/pollutant-graph-demo.git
cd pollutant-graph-demo
pip install -r requirements.txt
```

## Usage

Rule-based pipeline (no API key needed):

```bash
python main.py              # uses report.txt
python main.py other.txt    # uses another file
```

Example output:

```
WARNING: line 9 skipped: expected 6 columns, got 3
WARNING: line 10 skipped: Input should be 'unbedenklich', 'beobachten' or 'sanierungsbedürftig'
5 findings extracted, 51 triples in graph

Components not flagged for remediation (screening hint only):
  Bad: Fliesenkleber (Asbest)
  Büro 2: Wandfarbe (Blei)
  Dachboden: Dämmung (KMF)

Rooms containing Asbest:
  Bad
  Küche 1
```

LLM extractor (needs an API key; do not commit it):

```bash
# PowerShell
$env:ANTHROPIC_API_KEY = "your-key"
python llm_extract.py report.txt
python llm_extract.py report.txt openai:gpt-4o   # another provider (set OPENAI_API_KEY)
```

The default model can be changed with the `LLM_MODEL` environment variable. Use sample or
anonymized data only; do not send real reports to an external API unless you are allowed to.

## Tests

```bash
python -m pytest -q
```

## Status and limitations

- The rule-based parser handles one fixed table format (`Probe | Bauteil | Raum | Schadstoff | Menge | Bewertung`).
- The LLM extractor is tested with a mock model only; it has not been evaluated on real reports.
- The allowed rating values in `Rating` are examples and must be adapted to real reports.

## Next steps

- Evaluate the LLM extractor against reference data and trace runs with Langfuse
- Validate the graph with SHACL (`pyshacl`)
- Export the graph to Neo4j and add Cypher queries
- Test on free-text and messier reports
