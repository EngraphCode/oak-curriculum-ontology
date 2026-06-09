#!/bin/bash
# Local validation script that matches CI/CD exactly
set -eo pipefail

echo "======================================================================="
echo "LOCAL VALIDATION (matches CI/CD)"
echo "======================================================================="
echo ""

# Pre-flight checks
if [[ ! -f "scripts/merge_ttls_with_imports.py" ]]; then
    echo "❌ Error: scripts/merge_ttls_with_imports.py not found" >&2
    exit 1
fi

if [[ ! -f "ontology/oak-curriculum-constraints.ttl" ]]; then
    echo "❌ Error: ontology/oak-curriculum-constraints.ttl not found" >&2
    exit 1
fi

if [[ ! -f "ontology/oak-curriculum-ontology.ttl" ]]; then
    echo "❌ Error: ontology/oak-curriculum-ontology.ttl not found" >&2
    exit 1
fi

echo "Step 1: Merge TTL files and resolve imports..."
if command -v uv &> /dev/null; then
    uv run python3 scripts/merge_ttls_with_imports.py
else
    python3 scripts/merge_ttls_with_imports.py
fi

# Verify merge output exists
if [[ ! -f "/tmp/combined-data.ttl" ]]; then
    echo "❌ Error: Merge script did not produce /tmp/combined-data.ttl" >&2
    exit 1
fi

echo ""
echo "Step 2: Check Turtle syntax..."

# Run syntax check using rdflib
SYNTAX_CHECK_SCRIPT='
from rdflib import Graph
try:
    g = Graph()
    g.parse("/tmp/combined-data.ttl", format="turtle")
    print("✅ Merged Turtle syntax is valid")
except Exception as e:
    print(f"❌ Turtle syntax error: {e}")
    exit(1)
'

if command -v uv &> /dev/null; then
    uv run python3 -c "$SYNTAX_CHECK_SCRIPT"
else
    python3 -c "$SYNTAX_CHECK_SCRIPT"
fi

echo ""
echo "Step 3: Run SHACL validation..."

PYSHACL_ARGS=(
    --shacl ontology/oak-curriculum-constraints.ttl
    --ont-graph ontology/oak-curriculum-ontology.ttl
    --inference rdfs
    --abort
    --format human
    /tmp/combined-data.ttl
)

# Run pyshacl - prefer uv, then venv, then system; capture exit code without aborting script
set +e
if command -v uv &> /dev/null; then
    uv run pyshacl "${PYSHACL_ARGS[@]}" | tee /tmp/shacl-output.txt
elif [[ -f ".venv/bin/pyshacl" ]]; then
    .venv/bin/pyshacl "${PYSHACL_ARGS[@]}" | tee /tmp/shacl-output.txt
elif command -v pyshacl &> /dev/null; then
    pyshacl "${PYSHACL_ARGS[@]}" | tee /tmp/shacl-output.txt
else
    echo "❌ Error: pyshacl not found" >&2
    echo ""
    echo "Install it with:"
    echo "  uv add pyshacl"
    echo ""
    echo "Or without uv:"
    echo "  pip install pyshacl"
    exit 1
fi
set -e

# Only fail if there are actual violations; warnings alone are not failures
VIOLATIONS=$(grep -c "Constraint Violation" /tmp/shacl-output.txt || true)
if [ "${VIOLATIONS}" -gt 0 ]; then
    echo ""
    echo "❌ Found ${VIOLATIONS} constraint violation(s)"
    exit 1
elif grep -q "sh:Warning\|sh:Info" /tmp/shacl-output.txt; then
    echo ""
    echo "⚠️  Validation passed with warnings (no violations)"
fi

echo ""
echo "========================================================================"
echo "✅ All validation passed!"
echo "========================================================================"
