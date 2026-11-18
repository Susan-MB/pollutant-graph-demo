"""Pollutant report -> structured data -> knowledge graph -> question."""
from pydantic import BaseModel
from rdflib import Graph, Literal, Namespace, RDF, RDFS

EX = Namespace("https://example.org/")


# 1) Define what a "finding" looks like. Pydantic checks the data for us.
class Finding(BaseModel):
    sample_id: str
    component: str
    room: str
    pollutant: str
    rating: str


# 2) Extract findings from the report text (table rows separated by "|").
def extract(text: str) -> list[Finding]:
    findings = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) == 6 and cells[0].startswith("P-"):
            sample_id, component, room, pollutant, _amount, rating = cells
            findings.append(Finding(sample_id=sample_id, component=component,
                                    room=room, pollutant=pollutant, rating=rating))
    return findings


# 3) Put the findings into a knowledge graph: Room -> Component -> Finding.
def build_graph(findings: list[Finding]) -> Graph:
    g = Graph()
    for f in findings:
        room, comp = EX[f"room/{f.room}"], EX[f"component/{f.sample_id}"]
        g.add((room, RDF.type, EX.Room))
        g.add((room, RDFS.label, Literal(f.room)))
        g.add((room, EX.hasComponent, comp))
        g.add((comp, RDFS.label, Literal(f.component)))
        g.add((comp, EX.pollutant, Literal(f.pollutant)))
        g.add((comp, EX.rating, Literal(f.rating)))
    return g


# 4) Ask the graph a circular-economy question:
#    which components are NOT marked "sanierungsbedürftig" (must be remediated)?
QUERY = """
PREFIX ex: <https://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?room ?component WHERE {
  ?r ex:hasComponent ?c ; rdfs:label ?room .
  ?c rdfs:label ?component ; ex:rating ?rating .
  FILTER (?rating != "sanierungsbedürftig")
}
"""

if __name__ == "__main__":
    findings = extract(open("report.txt", encoding="utf-8").read())
    graph = build_graph(findings)
    print(f"{len(findings)} findings extracted, {len(graph)} triples in graph\n")
    print("Possibly reusable components:")
    for room, component in graph.query(QUERY):
        print(f"  {room}: {component}")
