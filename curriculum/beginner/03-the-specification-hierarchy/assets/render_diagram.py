"""Validate diagram-spec.json and deterministically render the Course 03 SVG."""

from __future__ import annotations

import json
from html import escape
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


def overlaps(first: dict, second: dict) -> bool:
    return not (
        first["x"] + first["width"] <= second["x"]
        or second["x"] + second["width"] <= first["x"]
        or first["y"] + first["height"] <= second["y"]
        or second["y"] + second["height"] <= first["y"]
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
        assert bounds["x"] + bounds["width"] <= width, f"outside canvas: {node['id']}"
        assert bounds["y"] + bounds["height"] <= height, f"outside canvas: {node['id']}"
        group = groups[node["group"]]["bounds"]
        assert bounds["x"] >= group["x"] and bounds["y"] >= group["y"]
        assert bounds["x"] + bounds["width"] <= group["x"] + group["width"]
        assert bounds["y"] + bounds["height"] <= group["y"] + group["height"]

    node_list = list(nodes.values())
    for index, node in enumerate(node_list):
        for other in node_list[index + 1 :]:
            assert not overlaps(node["bounds"], other["bounds"]), (
                f"overlap: {node['id']} and {other['id']}"
            )

    for edge in edges.values():
        source = nodes[edge["from"]["node"]]
        target = nodes[edge["to"]["node"]]
        route = [tuple(point) for point in edge["route"]]
        assert route[0] == port_position(source, edge["from"]["port"])
        assert route[-1] == port_position(target, edge["to"]["port"])
        for start, end in zip(route, route[1:], strict=False):
            assert start[0] == end[0] or start[1] == end[1], (
                f"diagonal route: {edge['id']}"
            )


def node_svg(node: dict, colors: dict) -> str:
    bounds = node["bounds"]
    palette = colors[node["type"]]
    x, y = bounds["x"], bounds["y"]
    width, height = bounds["width"], bounds["height"]
    label_y = y + 38 if node.get("subtitle") else y + height / 2
    labels = "".join(
        f'<tspan x="{x + 20}" dy="{0 if index == 0 else 22}">{escape(line)}</tspan>'
        for index, line in enumerate(node["label"])
    )
    subtitle = ""
    if node.get("subtitle"):
        subtitle_y = y + 82 if len(node["label"]) > 1 else y + 68
        subtitle = (
            f'<text x="{x + 20}" y="{subtitle_y}" class="subtitle">'
            f'{escape(node["subtitle"])}</text>'
        )
    return (
        f'<g id="node-{escape(node["id"])}">'
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="14" '
        f'fill="{palette["fill"]}" stroke="{palette["stroke"]}" stroke-width="2"/>'
        f'<text x="{x + 20}" y="{label_y}" class="node-label">{labels}</text>'
        f"{subtitle}</g>"
    )


def render(spec: dict) -> str:
    canvas = spec["canvas"]
    title = escape(spec["title"])
    description = escape(spec["output"]["alt_text"])
    colors = spec["style"]["semantic_colors"]
    parts = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-labelledby="title desc" '
            f'viewBox="0 0 {canvas["width"]} {canvas["height"]}">'
        ),
        f'<title id="title">{title}</title>',
        f'<desc id="desc">{description}</desc>',
        """<defs>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="7"
              flood-color="#16324F" flood-opacity="0.09"/>
          </filter>
          <marker id="arrow-primary" markerWidth="8" markerHeight="8"
            refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#2F6BFF"/>
          </marker>
          <marker id="arrow-governance" markerWidth="8" markerHeight="8"
            refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#087F7B"/>
          </marker>
          <marker id="arrow-secondary" markerWidth="8" markerHeight="8"
            refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#52606D"/>
          </marker>
          <marker id="arrow-stop" markerWidth="8" markerHeight="8"
            refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#D97706"/>
          </marker>
          <style>
            text { font-family: Inter, Arial, sans-serif; fill: #16324F; }
            .diagram-title { font-size: 30px; font-weight: 750; }
            .diagram-subtitle { font-size: 16px; fill: #52606D; }
            .group-label { font-size: 14px; font-weight: 750;
              letter-spacing: 1.5px; fill: #52606D; }
            .node-label { font-size: 17px; font-weight: 700; }
            .subtitle { font-size: 13px; fill: #52606D; }
            .edge-label { font-size: 13px; font-weight: 650; fill: #52606D;
              paint-order: stroke; stroke: #F7F9FC; stroke-width: 8px; }
          </style>
        </defs>""",
        f'<rect width="100%" height="100%" fill="{canvas["background"]}"/>',
        f'<text x="60" y="58" class="diagram-title">{title}</text>',
        (
            '<text x="60" y="88" class="diagram-subtitle">'
            "Applicability precedes precedence; uncertainty and unresolved authority "
            "stop execution."
            "</text>"
        ),
    ]

    for group in spec["groups"]:
        bounds = group["bounds"]
        parts.append(
            f'<g id="group-{escape(group["id"])}" filter="url(#shadow)">'
            f'<rect x="{bounds["x"]}" y="{bounds["y"]}" '
            f'width="{bounds["width"]}" height="{bounds["height"]}" rx="18" '
            f'fill="{group["fill"]}" stroke="{group["stroke"]}"/>'
            f'</g><text x="{bounds["x"] + 25}" y="{bounds["y"] + 38}" '
            f'class="group-label">{escape(group["label"])}</text>'
        )

    edge_styles = {
        "primary": ("#2F6BFF", "arrow-primary"),
        "governance": ("#087F7B", "arrow-governance"),
        "secondary": ("#52606D", "arrow-secondary"),
        "stop": ("#D97706", "arrow-stop"),
    }
    for edge in spec["edges"]:
        stroke, marker = edge_styles[edge["kind"]]
        points = " ".join(f"{x},{y}" for x, y in edge["route"])
        parts.append(
            f'<polyline id="edge-{escape(edge["id"])}" points="{points}" fill="none" '
            f'stroke="{stroke}" stroke-width="2.5" stroke-linecap="round" '
            f'stroke-linejoin="round" marker-end="url(#{marker})"/>'
        )
        if edge.get("label"):
            x, y = edge["label_position"]
            parts.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" class="edge-label">'
                f'{escape(edge["label"])}</text>'
            )

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
