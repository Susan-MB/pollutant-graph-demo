"""Pollutant report -> structured data -> knowledge graph -> question."""
import logging
import re
import sys
from enum import Enum
from pathlib import Path
from urllib.parse import quote

from pydantic import BaseModel, ValidationError
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD

EX = Namespace("https://example.org/")
log = logging.getLogger("pollutant-demo")


class Rating(str, Enum):
    """Allowed ratings. Adjust to the values your reports actually use."""
    OK = "unbedenklich"
    MONITOR = "beobachten"
    REMEDIATE = "sanierungsbedürftig"


class Finding(BaseModel):
    sample_id: str
    component: str
    room: str
    pollutant: str
    value: float | None = None   
    unit: str | None = None
    rating: Rating


_AMOUNT = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(.*?)\s*$")


def parse_amount(text: str) -> tuple[float | None, str | None]:
    """'12,5 mg/kg' -> (12.5, 'mg/kg'); 'n.n.' -> (None, None)."""
    m = _AMOUNT.match(text)
    if not m:
        return None, None
    return float(m.group(1).replace(",", ".")), (m.group(2) or None)


def extract(text: str) -> list[Finding]:
    findings = []
    for n, line in enumerate(text.splitlines(), start=1):
        cells = [c.strip() for c in line.split("|")]
        if not cells[0].startswith("P-"):
            continue  # header, separator or free text
        if len(cells) != 6:
            log.warning("line %d skipped: expected 6 columns, got %d", n, len(cells))
            continue
        sample_id, component, room, pollutant, amount, rating = cells
        value, unit = parse_amount(amount)
        try:
            findings.append(Finding(
                sample_id=sample_id, component=component, room=room,
                pollutant=pollutant, value=value, unit=unit,
                rating=rating.casefold(),
            ))
        except ValidationError as e:
            log.warning("line %d skipped: %s", n, e.errors()[0]["msg"])
    return findings


def build_graph(findings: list[Finding]) -> Graph:
    g = Graph()
    g.bind("ex", EX)
    for f in findings:
        room = EX[f"room/{quote(f.room, safe='')}"]
        comp = EX[f"component/{quote(f.sample_id, safe='')}"]
        poll = EX[f"pollutant/{quote(f.pollutant.casefold(), safe='')}"]

        g.add((room, RDF.type, EX.Room))
        g.add((room, RDFS.label, Literal(f.room)))
        g.add((room, EX.hasComponent, comp))

        g.add((comp, RDF.type, EX.Component))
        g.add((comp, RDFS.label, Literal(f.component)))
        g.add((comp, EX.contains, poll))
        g.add((comp, EX.rating, Literal(f.rating.value)))
        if f.value is not None:
            g.add((comp, EX.amount, Literal(f.value, datatype=XSD.double)))
        if f.unit:
            g.add((comp, EX.unit, Literal(f.unit)))

        g.add((poll, RDF.type, EX.Pollutant))
        g.add((poll, RDFS.label, Literal(f.pollutant)))
    return g


QUERY = f"""
PREFIX ex: <https://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?room ?component ?pollutant WHERE {{
  ?r ex:hasComponent ?c ; rdfs:label ?room .
  ?c rdfs:label ?component ; ex:rating ?rating ; ex:contains ?p .
  ?p rdfs:label ?pollutant .
  FILTER (?rating != "{Rating.REMEDIATE.value}")
}}
ORDER BY ?room ?component
"""

QUERY_ROOMS = """
PREFIX ex: <https://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?room WHERE {
  ?r ex:hasComponent ?c ; rdfs:label ?room .
  ?c ex:contains ?p .
  ?p rdfs:label ?name .
  FILTER (lcase(str(?name)) = lcase(?wanted))
}
ORDER BY ?room
"""


def main(path: str = "report.txt") -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    findings = extract(Path(path).read_text(encoding="utf-8"))
    graph = build_graph(findings)
    print(f"{len(findings)} findings extracted, {len(graph)} triples in graph\n")

    print("Components not flagged for remediation (screening hint only):")
    for room, component, pollutant in graph.query(QUERY):
        print(f"  {room}: {component} ({pollutant})")

    print("\nRooms containing Asbest:")
    for (room,) in graph.query(QUERY_ROOMS, initBindings={"wanted": Literal("Asbest")}):
        print(f"  {room}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
