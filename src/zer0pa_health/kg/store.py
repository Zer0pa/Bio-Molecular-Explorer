"""JSONL-backed KG store with NetworkX in-memory view.

Files:
  kg/nodes.jsonl         — append-only nodes
  kg/edges.jsonl         — append-only edges
  kg/cardiac_seed.jsonl  — committed seed (bootstrap data)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import networkx as nx

from zer0pa_health.kg.schema import KGEdge, KGNode


class KGStore:
    def __init__(self, kg_root: Path) -> None:
        self.kg_root = kg_root
        self.kg_root.mkdir(parents=True, exist_ok=True)
        self.nodes_path = self.kg_root / "nodes.jsonl"
        self.edges_path = self.kg_root / "edges.jsonl"

    def add_node(self, node: KGNode) -> None:
        with self.nodes_path.open("a", encoding="utf-8") as fh:
            fh.write(node.model_dump_json() + "\n")

    def add_edge(self, edge: KGEdge) -> None:
        with self.edges_path.open("a", encoding="utf-8") as fh:
            fh.write(edge.model_dump_json() + "\n")

    def add_nodes(self, nodes: Iterable[KGNode]) -> None:
        with self.nodes_path.open("a", encoding="utf-8") as fh:
            for n in nodes:
                fh.write(n.model_dump_json() + "\n")

    def add_edges(self, edges: Iterable[KGEdge]) -> None:
        with self.edges_path.open("a", encoding="utf-8") as fh:
            for e in edges:
                fh.write(e.model_dump_json() + "\n")

    def iter_nodes(self) -> Iterable[KGNode]:
        if not self.nodes_path.exists():
            return
        with self.nodes_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield KGNode.model_validate_json(line)

    def iter_edges(self) -> Iterable[KGEdge]:
        if not self.edges_path.exists():
            return
        with self.edges_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield KGEdge.model_validate_json(line)

    def to_networkx(self) -> nx.MultiDiGraph:
        g = nx.MultiDiGraph()
        for n in self.iter_nodes():
            g.add_node(n.node_id, node_type=n.node_type, **n.properties)
        for e in self.iter_edges():
            g.add_edge(
                e.source_node_id,
                e.target_node_id,
                key=e.edge_id,
                edge_type=e.edge_type,
                **e.properties,
            )
        return g

    def load_seed(self, seed_path: Path) -> int:
        """Load a seed file into the store. Format: JSONL of {"kind":"node","data":...} or {"kind":"edge","data":...}."""
        n = 0
        with seed_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec["kind"] == "node":
                    self.add_node(KGNode.model_validate(rec["data"]))
                elif rec["kind"] == "edge":
                    self.add_edge(KGEdge.model_validate(rec["data"]))
                else:
                    raise ValueError(f"unknown seed kind: {rec['kind']!r}")
                n += 1
        return n
