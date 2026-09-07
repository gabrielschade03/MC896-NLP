"""Gera uma página HTML interativa com o grafo e a linha do tempo dos casos."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES = ROOT / "outputs" / "nodes.csv"
DEFAULT_EDGES = ROOT / "outputs" / "edges.csv"
DEFAULT_CASES = ROOT / "data" / "prepared" / "development.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "graph.html"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "graph.html"
PLACEHOLDER = "/*__GRAPH_DATA__*/ null"

EVENT_TYPES = ("Symptom", "Exam", "Condition", "Treatment")


def read_csv(path):
    # newline="" preserva o \r\n do arquivo: os offsets de nodes.csv foram
    # calculados sobre o texto lido dessa forma por build_graph.py.
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _attributes(value):
    """Converte a coluna ``attributes`` em dicionário."""
    if not value:
        return {}
    return json.loads(value)


def _optional_int(value):
    return int(value) if value not in (None, "") else None


def build_nodes(rows):
    nodes = []
    for row in rows:
        nodes.append({
            "id": row["node_id"],
            "case_id": row["case_id"],
            "type": row["type"],
            "label": row["label"],
            "mention": row["mention_text"],
            "sentence_id": _optional_int(row["sentence_id"]),
            "start": _optional_int(row["start"]),
            "end": _optional_int(row["end"]),
            "attrs": _attributes(row["attributes"]),
            "evidence": row["evidence"],
        })
    return nodes


def build_edges(rows):
    edges = []
    for row in rows:
        edges.append({
            "id": row["edge_id"],
            "case_id": row["case_id"],
            "source": row["source_id"],
            "target": row["target_id"],
            "relation": row["relation"],
            "attrs": _attributes(row["attributes"]),
            "evidence": row["evidence"],
        })
    return edges


def build_cases(case_rows, nodes):
    """Une os metadados de cada caso ao texto original e à contagem de nós."""
    counts = defaultdict(Counter)
    for node in nodes:
        counts[node["case_id"]][node["type"]] += 1

    texts = {row["case_id"]: row for row in case_rows}
    cases = []
    for case_id in sorted(counts):
        row = texts.get(case_id, {})
        case_node = next(
            (node for node in nodes if node["case_id"] == case_id and node["type"] == "Case"),
            None,
        )
        attrs = case_node["attrs"] if case_node else {}
        cases.append({
            "case_id": case_id,
            "article_id": row.get("article_id") or attrs.get("article_id", ""),
            "title": row.get("title") or attrs.get("title", ""),
            "age": row.get("age") or attrs.get("age", ""),
            "gender": row.get("gender") or attrs.get("gender", ""),
            "text": row.get("case_text", ""),
            "counts": dict(counts[case_id]),
        })
    return cases


def build_overview(nodes, edges):
    """Agrega as ocorrências por rótulo normalizado, somando todos os casos."""
    by_id = {node["id"]: node for node in nodes}
    aggregated = {}
    for node in nodes:
        if node["type"] not in EVENT_TYPES:
            continue
        key = f"agg:{node['type']}:{node['label']}"
        entry = aggregated.setdefault(key, {
            "id": key,
            "type": node["type"],
            "label": node["label"],
            "count": 0,
            "cases": [],
            "aggregate": True,
            "attrs": {},
        })
        entry["count"] += 1
        if node["case_id"] not in entry["cases"]:
            entry["cases"].append(node["case_id"])

    def aggregate_id(node_id):
        node = by_id.get(node_id)
        if node is None or node["type"] not in EVENT_TYPES:
            return None
        return f"agg:{node['type']}:{node['label']}"

    pairs = Counter()
    for edge in edges:
        source = aggregate_id(edge["source"])
        target = aggregate_id(edge["target"])
        if source is None or target is None or source == target:
            continue
        pairs[(source, target, edge["relation"])] += 1

    overview_edges = [
        {
            "id": f"agg_edge_{index:04d}",
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight,
            "attrs": {},
            "evidence": "",
        }
        for index, ((source, target, relation), weight) in enumerate(sorted(pairs.items()), start=1)
    ]
    nodes_sorted = sorted(aggregated.values(), key=lambda item: (-item["count"], item["label"]))
    return {"nodes": nodes_sorted, "edges": overview_edges}


def build_payload(node_rows, edge_rows, case_rows):
    nodes = build_nodes(node_rows)
    edges = build_edges(edge_rows)
    cases = build_cases(case_rows, nodes)
    return {
        "nodes": nodes,
        "edges": edges,
        "cases": cases,
        "overview": build_overview(nodes, edges),
        "summary": {
            "cases": len(cases),
            "nodes": len(nodes),
            "edges": len(edges),
            "before": sum(1 for edge in edges if edge["relation"] == "BEFORE"),
            "types": dict(Counter(node["type"] for node in nodes)),
        },
    }


def render_html(payload, template_path=TEMPLATE_PATH):
    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"Marcador {PLACEHOLDER!r} não encontrado em {template_path}.")
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Evita que o texto de um caso feche o bloco <script> da página.
    data = data.replace("</", "<\\/")
    return template.replace(PLACEHOLDER, data)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Gera graph.html a partir do grafo extraído.")
    parser.add_argument("--nodes", type=Path, default=DEFAULT_NODES)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--template", type=Path, default=TEMPLATE_PATH)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    payload = build_payload(
        read_csv(args.nodes), read_csv(args.edges), read_csv(args.cases)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(payload, args.template), encoding="utf-8")
    summary = payload["summary"]
    print(f"Casos: {summary['cases']}")
    print(f"Nós: {summary['nodes']}")
    print(f"Arestas: {summary['edges']} (BEFORE: {summary['before']})")
    print(f"Visualização: {args.output}")


if __name__ == "__main__":
    main()
