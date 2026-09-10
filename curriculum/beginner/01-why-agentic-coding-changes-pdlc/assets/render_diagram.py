"""Validate diagram-spec.json and deterministically render the course SVG."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "diagram-spec.json"


def port_position(node: dict, port_name: str) -> tuple[float, float]:
    bounds = node["bounds"]
    port = node["ports"][port_name]
    side, offset = port["side"], port["offset"]
    if side == "left":
        return bounds["x"], bounds["y"] + bounds["height"] * offset
    if side == "right":
        return bounds["x"] + bounds["width"], bounds["y"] + bounds["height"] * offset
    if side == "top":
        return bounds["x"] + bounds["width"] * offset, bounds["y"]
    if side == "bottom":
        return bounds["x"] + bounds["width"] * offset, bounds["y"] + bounds["height"]
    raise ValueError(f"unsupported port side: {side}")


def overlaps(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def validate(spec: dict) -> None:
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    groups = {group["id"]: group for group in spec["groups"]}
    nodes = {node["id"]: node for node in spec["nodes"]}
    edges = {edge["id"]: edge for edge in spec["edges"]}
    assert len(groups) == len(spec["groups"]), "duplicate group ID"
    assert len(nodes) == len(spec["nodes"]), "duplicate node ID"
    assert len(edges) == len(spec["edges"]), "duplicate edge ID"

    for node in nodes.values():
        bounds = node["bounds"]
        assert bounds["x"] >= 0 and bounds["y"] >= 0, f"negative bounds: {node['id']}"
        assert bounds["x"] + bounds["width"] <= width, f"node outside canvas: {node['id']}"
        assert bounds["y"] + bounds["height"] <= height, f"node outside canvas: {node['id']}"
        group = groups[node["group"]]["bounds"]
        assert bounds["x"] >= group["x"] and bounds["y"] >= group["y"], f"node outside group: {node['id']}"
        assert bounds["x"] + bounds["width"] <= group["x"] + group["width"], f"node outside group: {node['id']}"
        assert bounds["y"] + bounds["height"] <= group["y"] + group["height"], f"node outside group: {node['id']}"

    node_list = list(nodes.values())
    for index, node in enumerate(node_list):
        for other in node_list[index + 1 :]:
            assert not overlaps(node["bounds"], other["bounds"]), f"overlap: {node['id']} and {other['id']}"

    for edge in edges.values():
        source = nodes[edge["from"]["node"]]
        target = nodes[edge["to"]["node"]]
        source_port = edge["from"]["port"]
        target_port = edge["to"]["port"]
        assert source_port in source["ports"], f"missing source port: {edge['id']}"
        assert target_port in target["ports"], f"missing target port: {edge['id']}"
        route = [tuple(point) for point in edge["route"]]
        assert route[0] == port_position(source, source_port), f"detached source: {edge['id']}"
        assert route[-1] == port_position(target, target_port), f"detached target: {edge['id']}"
        for start, end in zip(route, route[1:]):
            assert start[0] == end[0] or start[1] == end[1], f"diagonal route: {edge['id']}"


def node_svg(node: dict, colors: dict) -> str:
    bounds = node["bounds"]
    palette = colors[node["type"]]
    x, y, width, height = bounds["x"], bounds["y"], bounds["width"], bounds["height"]
    label_lines = node["label"]
    label_y = y + 40 if node.get("subtitle") else y + height / 2
    tspans = "".join(
        f'<tspan x="{x + 20}" dy="{0 if index == 0 else 22}">{escape(line)}</tspan>'
        for index, line in enumerate(label_lines)
    )
    subtitle = ""
    if node.get("subtitle"):
        subtitle = f'<text x="{x + 20}" y="{y + 70}" class="subtitle">{escape(node["subtitle"])}</text>'
    return (
        f'<g id="node-{escape(node["id"])}">'
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="14" '
        f'fill="{palette["fill"]}" stroke="{palette["stroke"]}" stroke-width="2"/>'
        f'<text x="{x + 20}" y="{label_y}" class="node-label">{tspans}</text>'
        f'{subtitle}</g>'
    )


def render(spec: dict) -> str:
    canvas = spec["canvas"]
    colors = spec["style"]["semantic_colors"]
    title = escape(spec["title"])
    description = escape(spec["output"]["alt_text"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" '
        f'viewBox="0 0 {canvas["width"]} {canvas["height"]}" width="{canvas["width"]}" height="{canvas["height"]}">',
        f'<title id="title">{title}</title>',
        f'<desc id="desc">{description}</desc>',
        """<defs>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="7" flood-color="#16324F" flood-opacity="0.09"/>
          </filter>
          <marker id="arrow-primary" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#2F6BFF"/>
          </marker>
          <marker id="arrow-governance" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#087F7B"/>
          </marker>
          <marker id="arrow-feedback" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#D97706"/>
          </marker>
          <style>
            text { font-family: Inter, Arial, sans-serif; fill: #16324F; }
            .diagram-title { font-size: 30px; font-weight: 750; }
            .diagram-subtitle { font-size: 16px; fill: #52606D; }
            .group-label { font-size: 15px; font-weight: 750; letter-spacing: 1.8px; fill: #52606D; }
            .node-label { font-size: 17px; font-weight: 700; }
            .subtitle { font-size: 13px; fill: #52606D; }
            .edge-label { font-size: 13px; font-weight: 650; fill: #52606D; paint-order: stroke; stroke: #F7F9FC; stroke-width: 8px; stroke-linejoin: round; }
          </style>
        </defs>""",
        f'<rect width="100%" height="100%" fill="{canvas["background"]}"/>',
        f'<text x="60" y="58" class="diagram-title">{title}</text>',
        '<text x="60" y="88" class="diagram-subtitle">Inherited intent constrains execution; evidence and runtime signals revise the next change.</text>',
    ]

    for group in spec["groups"]:
        bounds = group["bounds"]
        parts.append(
            f'<g id="group-{escape(group["id"])}" filter="url(#shadow)">'
            f'<rect x="{bounds["x"]}" y="{bounds["y"]}" width="{bounds["width"]}" height="{bounds["height"]}" rx="18" '
            f'fill="{group["fill"]}" stroke="{group["stroke"]}" stroke-width="1.5"/>'
            f'</g><text x="{bounds["x"] + 30}" y="{bounds["y"] + 42}" class="group-label">{escape(group["label"])}</text>'
        )

    edge_styles = {
        "primary": ("#2F6BFF", "arrow-primary", "2.5"),
        "governance": ("#087F7B", "arrow-governance", "2.5"),
        "feedback": ("#D97706", "arrow-feedback", "2.5"),
    }
    for edge in spec["edges"]:
        stroke, marker, width = edge_styles[edge["kind"]]
        points = " ".join(f"{x},{y}" for x, y in edge["route"])
        parts.append(
            f'<polyline id="edge-{escape(edge["id"])}" points="{points}" fill="none" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" '
            f'marker-end="url(#{marker})"/>'
        )
        if edge.get("label"):
            x, y = edge["label_position"]
            parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" class="edge-label">{escape(edge["label"])}</text>')

    for node in spec["nodes"]:
        parts.append(node_svg(node, colors))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    validate(spec)
    destination = HERE / spec["output"]["svg"]
    destination.write_text(render(spec), encoding="utf-8")
    print(f"validated {SPEC_PATH.name}")
    print(f"rendered {destination.name}")


if __name__ == "__main__":
    main()

