# Pollutant graph demo

Turns a (synthetic) German pollutant report into a small knowledge graph and
asks which building components could possibly be reused.

    pip install pydantic rdflib
    python main.py

## How it works
1. **Extract**: read the table rows of the report into typed `Finding` objects (Pydantic).
2. **Graph**: store them as triples: Room -> Component -> pollutant/rating (RDF, rdflib).
3. **Query**: SPARQL finds components that don't need remediation.

## Limitations
- Only works on this table format; real reports are messy PDFs.
- "Reusable" is a simplification. Real rules depend on pollutant and regulation.

## Next steps
Replace the extraction step with an LLM (PydanticAI), load the graph into Neo4j,
and measure extraction quality against hand-labelled examples.
