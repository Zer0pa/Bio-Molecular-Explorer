"""Pure Graphviz DOT emitter for L3 unit op sequences.

No graphviz binary required — this module only emits DOT syntax strings.
The caller (or a visualisation tool) renders the DOT if desired.

Function
--------
unit_ops_to_dot(ops: list[L3UnitOp]) -> str
    Return a valid DOT digraph string where:
    - Each unit op is a node labelled with its name and kind.
    - Edges connect the outputs of op N to the inputs of op N+1 by
      matching material flow roles/SMILES.
    - The graph is syntactically valid Graphviz DOT (no binary required).
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.contracts.l3 import L3UnitOp


def unit_ops_to_dot(ops: list[L3UnitOp]) -> str:
    """Emit a Graphviz DOT digraph from an ordered list of L3UnitOp objects.

    Each unit op becomes a rectangular node.  Edges connect consecutive ops
    and are labelled with the product/output material role.

    Parameters
    ----------
    ops:
        Ordered sequence of unit ops (as produced by L3StubAdapter.process).

    Returns
    -------
    str
        A syntactically valid Graphviz DOT string.  Can be piped to
        ``dot -Tpng`` if graphviz is installed, but no binary is required
        for the string to be emitted.
    """
    if not ops:
        return "digraph process_graph {\n    // empty\n}\n"

    lines: list[str] = ["digraph process_graph {", "    rankdir=LR;", "    node [shape=box];"]

    # Declare all nodes
    for i, op in enumerate(ops):
        label = f"{op.kind.value}\\n{op.name}"
        lines.append(f'    n{i} [label="{_escape_dot(label)}"];')

    # Edges: connect op[i] -> op[i+1], labelled by output role
    for i in range(len(ops) - 1):
        src_op = ops[i]
        # Use first output's role/SMILES as edge label
        if src_op.outputs:
            flow = src_op.outputs[0]
            smiles_label = (
                _escape_dot(flow.canonical_smiles[:20] + "...")
                if flow.canonical_smiles and len(flow.canonical_smiles) > 20
                else _escape_dot(flow.canonical_smiles or "")
            )
            edge_label = f"{flow.role}\\n{smiles_label}\\n{flow.mass_kg:.3f} kg"
        else:
            edge_label = "flow"
        lines.append(f'    n{i} -> n{i + 1} [label="{edge_label}"];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def _escape_dot(text: str) -> str:
    """Escape double-quotes and backslashes for DOT string literals."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
