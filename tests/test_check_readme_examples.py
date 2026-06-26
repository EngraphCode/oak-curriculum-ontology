"""Unit tests for the README drift checker."""

from rdflib import Graph

import check_readme_examples as cre

CURRIC = "https://w3id.org/uk/oak/curriculum/ontology/"
NATCURRIC = "https://w3id.org/uk/oak/curriculum/nationalcurriculum/"

SAMPLE = """\
Intro text

```turtle
@prefix ex: <http://example.org/> .
ex:a ex:b ex:c .
```

```sparql
SELECT ?s WHERE { ?s ?p ?o }
```
"""


def _graph(ttl: str) -> Graph:
    g = Graph()
    g.parse(data=ttl, format="turtle")
    return g


def lessons(n: int) -> Graph:
    triples = "\n".join(f"ex:l{i} a curric:Lesson ." for i in range(n))
    return _graph(f"@prefix curric: <{CURRIC}> .\n@prefix ex: <http://example.org/> .\n{triples}")


def test_extract_code_blocks_finds_each_language() -> None:
    turtle = cre.extract_code_blocks(SAMPLE, "turtle")
    sparql = cre.extract_code_blocks(SAMPLE, "sparql")
    assert len(turtle) == 1
    assert len(sparql) == 1
    assert turtle[0][1].startswith("@prefix")
    # line numbers point at the opening fence
    assert turtle[0][0] == 3


def test_extract_code_blocks_ignores_other_languages() -> None:
    assert cre.extract_code_blocks(SAMPLE, "json") == []


def test_instance_counts_accept_matching_claims() -> None:
    assert cre.check_instance_counts("We publish 2 lessons.", lessons(2)) == []


def test_instance_counts_reject_wrong_claims() -> None:
    errors = cre.check_instance_counts("We publish 3 lessons.", lessons(2))
    assert len(errors) == 1
    assert "claims 3 lessons" in errors[0]


def test_instance_counts_skip_year_and_key_stage_ordinals() -> None:
    md = "Find all Year 7 programmes and Key Stage 4 units"
    assert cre.check_instance_counts(md, lessons(0)) == []


def test_instance_counts_parse_thousands_separators() -> None:
    errors = cre.check_instance_counts("All 1,202 lessons.", lessons(2))
    assert len(errors) == 1
    assert "1,202" in errors[0]


def test_instance_counts_match_table_rows() -> None:
    md = "| Lessons | 2 | per-lesson data |"
    assert cre.check_instance_counts(md, lessons(2)) == []
    assert len(cre.check_instance_counts(md, lessons(5))) == 1


def test_counts_check_classes_and_shapes() -> None:
    ontology = _graph(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/> .
        ex:A a owl:Class . ex:B a owl:Class .
        """
    )
    constraints = _graph(
        """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .
        ex:AShape a sh:NodeShape .
        """
    )
    assert cre.check_counts("2 classes and 1 shapes", ontology, constraints) == []
    errors = cre.check_counts("5 classes", ontology, constraints)
    assert len(errors) == 1


def test_turtle_blocks_flag_unknown_properties_and_entities() -> None:
    ontology = _graph(
        f"""
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix curric: <{CURRIC}> .
        curric:goodProp a owl:ObjectProperty .
        """
    )
    data = _graph(
        f"""
        @prefix natcurric: <{NATCURRIC}> .
        natcurric:x natcurric:p natcurric:thing .
        """
    )
    good = f"""```turtle
@prefix curric: <{CURRIC}> .
@prefix natcurric: <{NATCURRIC}> .
natcurric:x curric:goodProp natcurric:thing .
```"""
    assert cre.check_turtle_blocks(good, ontology, data) == []

    bad = good.replace("goodProp", "fakeProp")
    errors = cre.check_turtle_blocks(bad, ontology, data)
    assert any("not defined in the ontology" in e for e in errors)

    missing = good.replace("natcurric:thing", "natcurric:ghost")
    errors = cre.check_turtle_blocks(missing, ontology, data)
    assert any("does not exist in the data" in e for e in errors)
