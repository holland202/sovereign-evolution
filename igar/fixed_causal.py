"""
Fixed causal identification: real d-separation, not a hardcoded True.
(Copy of sovereign_ops/fixed_causal.py -- kept alongside IGAR since
igar_core.py imports it directly. See sovereign_ops/ for the canonical
version and its own README.)

d-separation algorithm (Pearl): a path is blocked by set Z if it contains
  - a chain or fork node in Z, or
  - a collider node NOT in Z and none of its descendants in Z.
X and Y are d-separated by Z if ALL paths between them are blocked.

Candidate search order is sorted for determinism (same DAG always returns
the same valid adjustment set across runs, even though multiple valid
sets can exist).
"""
from typing import Dict, List, Set, Tuple
from itertools import combinations


class CausalDAG:
    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: List[Tuple[str, str]] = []  # (parent, child)

    def add_node(self, name):
        self.nodes.add(name)

    def add_edge(self, parent, child):
        self.edges.append((parent, child))

    def parents(self, node):
        return {p for p, c in self.edges if c == node}

    def children(self, node):
        return {c for p, c in self.edges if p == node}

    def ancestors(self, node):
        seen, stack = set(), list(self.parents(node))
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(self.parents(n))
        return seen

    def _neighbors_undirected(self, node):
        return self.parents(node) | self.children(node)

    def _all_paths(self, start, end, path=None):
        """All simple undirected paths from start to end (for small DAGs)."""
        if path is None:
            path = [start]
        if start == end:
            return [path]
        paths = []
        for nxt in self._neighbors_undirected(start):
            if nxt not in path:
                paths.extend(self._all_paths(nxt, end, path + [nxt]))
        return paths

    def _edge_type(self, a, b, c):
        """Determine if b is a chain/fork/collider on path a-b-c."""
        a_to_b = (a, b) in self.edges
        b_to_a = (b, a) in self.edges
        b_to_c = (b, c) in self.edges
        c_to_b = (c, b) in self.edges
        if a_to_b and b_to_c:
            return "chain"       # a -> b -> c
        if c_to_b and b_to_a:
            return "chain"       # c -> b -> a
        if b_to_a and b_to_c:
            return "fork"        # a <- b -> c
        if a_to_b and c_to_b:
            return "collider"    # a -> b <- c
        return "chain"  # fallback for malformed adjacency

    def path_is_blocked(self, path: List[str], Z: Set[str]) -> bool:
        for i in range(1, len(path) - 1):
            a, b, c = path[i - 1], path[i], path[i + 1]
            etype = self._edge_type(a, b, c)
            if etype in ("chain", "fork"):
                if b in Z:
                    return True  # blocked at non-collider in Z
            elif etype == "collider":
                descendants_b = self._descendants(b)
                if b not in Z and not (descendants_b & Z):
                    return True  # blocked: collider not in Z, no descendant in Z either
        return False

    def _descendants(self, node):
        seen, stack = set(), list(self.children(node))
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(self.children(n))
        return seen

    def d_separated(self, X: str, Y: str, Z: Set[str]) -> bool:
        """True if X and Y are d-separated given Z (all paths blocked)."""
        paths = self._all_paths(X, Y)
        if not paths:
            return True
        return all(self.path_is_blocked(p, Z) for p in paths)


def find_valid_backdoor_set(dag: CausalDAG, treatment: str, outcome: str, max_size=3):
    """
    Real backdoor criterion search:
    Z satisfies backdoor if (1) no node in Z descends from treatment, and
    (2) Z d-separates treatment and outcome in the graph with edges OUT of
    treatment removed (i.e., blocks all back-door paths).
    Returns first valid Z found (deterministic, sorted search order), or None.
    Note: a DAG can have multiple valid backdoor sets. This returns one
    valid set, not necessarily the only one or the "smallest" one.
    """
    treatment_descendants = dag._descendants(treatment)
    candidates = sorted(n for n in dag.nodes if n not in (treatment, outcome)
                         and n not in treatment_descendants)

    # build backdoor graph: remove edges out of treatment
    backdoor_dag = CausalDAG()
    backdoor_dag.nodes = set(dag.nodes)
    backdoor_dag.edges = [(p, c) for (p, c) in dag.edges if p != treatment]

    for size in range(0, min(max_size, len(candidates)) + 1):
        for Z in combinations(candidates, size):
            if backdoor_dag.d_separated(treatment, outcome, set(Z)):
                return set(Z)
    return None
