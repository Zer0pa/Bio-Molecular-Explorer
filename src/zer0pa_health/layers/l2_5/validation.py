"""Pure-Python validators for L2.5 retrosynthesis route quality.

No RDKit required. These operate on SMILES/RXNSMILES strings only.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import re

# Pattern matching atom-map index in SMILES notation: [<atom>:<int>]
_ATOMMAP_RE = re.compile(r":\d+\]")


def validate_rxnsmiles(rxn: str) -> tuple[bool, str]:
    """Validate a reaction SMILES string.

    Accepts:
      - 'reactants>>products' format
      - 'reactants>reagents>products' format

    Returns:
        (ok, reason) — if ok is False, reason explains the failure.
    """
    if not isinstance(rxn, str) or not rxn.strip():
        return False, "rxnsmiles is empty or not a string"

    if ">>" not in rxn and rxn.count(">") < 2:
        return False, "rxnsmiles must contain '>>' or 'reactants>reagents>products'"

    # Split on ">>" first; if not present, split on ">" giving 3 parts
    if ">>" in rxn:
        parts = rxn.split(">>", 1)
        reactants = parts[0].strip()
        products = parts[1].strip()
    else:
        segments = rxn.split(">")
        if len(segments) < 3:
            return False, "rxnsmiles 'reactants>reagents>products' must have at least two '>' characters"
        reactants = segments[0].strip()
        products = segments[2].strip()

    if not reactants:
        return False, "rxnsmiles reactants side is empty"
    if not products:
        return False, "rxnsmiles products side is empty"

    # Check balanced parentheses across full string
    if rxn.count("(") != rxn.count(")"):
        return False, "unbalanced parentheses in rxnsmiles"

    # Check balanced brackets across full string
    if rxn.count("[") != rxn.count("]"):
        return False, "unbalanced brackets in rxnsmiles"

    return True, "ok"


def validate_atom_map(atom_mapped_rxn: str) -> tuple[bool, str]:
    """Validate that an atom-mapped reaction SMILES has actual atom-map indices.

    Requirements:
      - At least one ':<int>]' pattern present in the reactants side.
      - At least one ':<int>]' pattern present in the products side.
      - At least one mapped index integer appears on BOTH sides (tracking across reaction).

    Returns:
        (ok, reason) — if ok is False, reason explains the failure.
    """
    if not isinstance(atom_mapped_rxn, str) or not atom_mapped_rxn.strip():
        return False, "atom_mapped_rxn is empty or not a string"

    # Split into reactants/products portions
    if ">>" in atom_mapped_rxn:
        parts = atom_mapped_rxn.split(">>", 1)
        reactants_side = parts[0]
        products_side = parts[1]
    elif atom_mapped_rxn.count(">") >= 2:
        segments = atom_mapped_rxn.split(">")
        reactants_side = segments[0]
        products_side = segments[2]
    else:
        return False, "atom_mapped_rxn has no '>>' or '>reagents>' separator"

    # Extract integer atom-map indices from each side
    def _extract_indices(side: str) -> set[int]:
        return {int(m.group()[1:-1]) for m in _ATOMMAP_RE.finditer(side)}

    reactant_indices = _extract_indices(reactants_side)
    product_indices = _extract_indices(products_side)

    if not reactant_indices:
        return False, "no atom-map indices found in reactants side (expected ':<int>]' patterns)"
    if not product_indices:
        return False, "no atom-map indices found in products side (expected ':<int>]' patterns)"

    shared = reactant_indices & product_indices
    if not shared:
        return False, (
            f"no atom-map indices shared between reactants {sorted(reactant_indices)} "
            f"and products {sorted(product_indices)}; atoms are not tracked across the reaction"
        )

    return True, "ok"
