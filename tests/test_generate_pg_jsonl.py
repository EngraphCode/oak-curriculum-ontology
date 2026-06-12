"""Unit and round-trip tests for the property-graph JSONL generator."""

import json
import math
from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import XSD

import generate_pg_jsonl as pg

FIXTURE = """\
@prefix ex: <http://example.org/voc/> .
@prefix d: <http://example.org/data/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:Thing a owl:Class .
d:a a ex:Thing ;
  rdfs:label "Thing A" ;
  ex:size "3"^^xsd:integer ;
  ex:links d:b ;
  ex:refs d:ghost .
d:b a ex:Thing ;
  rdfs:label "Thing B" .
"""


def test_local_name() -> None:
    assert pg.local_name(URIRef("http://example.org/voc/Thing")) == "Thing"
    assert pg.local_name(URIRef("http://example.org/voc#Frag")) == "Frag"


def test_stub_namespace_label() -> None:
    uri = "https://w3id.org/uk/oak/curriculum/nationalcurriculum/year-group-1"
    assert pg.stub_namespace_label(uri) == "nationalcurriculum"


def test_coerce_literal() -> None:
    assert pg.coerce_literal(Literal("true", datatype=XSD.boolean)) is True
    assert pg.coerce_literal(Literal("3", datatype=XSD.integer)) == 3
    assert math.isclose(pg.coerce_literal(Literal("1.5", datatype=XSD.decimal)), 1.5)
    assert pg.coerce_literal(Literal("text")) == "text"


def test_generate_round_trip(tmp_path: Path) -> None:
    input_ttl = tmp_path / "fixture.ttl"
    input_ttl.write_text(FIXTURE, encoding="utf-8")
    out = tmp_path / "dist"
    out.mkdir()

    stats = pg.generate(input_ttl, out)

    # 2 typed instances + 1 dangling reference stub
    assert stats == {"nodes": 3, "relationships": 2, "stubs": 1}

    nodes = {
        obj["id"]: obj
        for obj in map(json.loads, (out / "nodes.jsonl").read_text().splitlines())
    }
    a = nodes["http://example.org/data/a"]
    assert a["labels"] == ["Thing"]
    assert a["properties"]["name"] == "Thing A"  # rdfs:label -> name
    assert a["properties"]["size"] == 3  # xsd:integer coerced

    ghost = nodes["http://example.org/data/ghost"]
    assert ghost["labels"] == ["ExternalReference"]
    assert ghost["properties"]["namespace"] == "data"

    rels = [
        json.loads(line)
        for line in (out / "relationships.jsonl").read_text().splitlines()
    ]
    types = sorted(r["type"] for r in rels)
    assert types == ["links", "refs"]
    # every endpoint exists in the node set
    for rel in rels:
        assert rel["startNodeId"] in nodes
        assert rel["endNodeId"] in nodes
