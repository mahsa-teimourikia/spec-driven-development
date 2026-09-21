"""Validate diagram-spec.json and deterministically render the Course 07 SVG."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "diagram-spec.json"


def port_position(node: dict, name: str) -> tuple[float, float]:
    bounds, port = node["bounds"], node["ports"][name]
    side, offset = port["side"], port["offset"]
    if side == "left":
        return bounds["x"], bounds["y"] + bounds["height"] * offset
    if side == "right":
        return bounds["x"] + bounds["width"], bounds["y"] + bounds["height"] * offset
    if side == "top":
        return bounds["x"] + bounds["width"] * offset, bounds["y"]
    if side == "bottom":
        return bounds["x"] + bounds["width"] * offset, bounds["y"] + bounds["height"]
    raise ValueError(f"unsupported side: {side}")


def overlaps(first: dict, second: dict) -> bool:
    return not (
        first["x"] + first["width"] <= second["x"]
        or second["x"] + second["width"] <= first["x"]
        or first["y"] + first["height"] <= second["y"]
        or second["y"] + second["height"] <= first["y"]
    )


def validate(spec: dict) -> None:
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    groups = {item["id"]: item for item in spec["groups"]}
    nodes = {item["id"]: item for item in spec["nodes"]}
    assert len(groups) == len(spec["groups"])
    assert len(nodes) == len(spec["nodes"])
    assert len({item["id"] for item in spec["edges"]}) == len(spec["edges"])
    for node in nodes.values():
        bounds = node["bounds"]
        group = groups[node["group"]]["bounds"]
        assert 0 <= bounds["x"] and bounds["x"] + bounds["width"] <= width
        assert 0 <= bounds["y"] and bounds["y"] + bounds["height"] <= height
        assert group["x"] <= bounds["x"] and group["y"] <= bounds["y"]
        assert bounds["x"] + bounds["width"] <= group["x"] + group["width"]
        assert bounds["y"] + bounds["height"] <= group["y"] + group["height"]
    node_list = list(nodes.values())
    for index, node in enumerate(node_list):
        for other in node_list[index + 1 :]:
            assert not overlaps(node["bounds"], other["bounds"]), f"overlap: {node['id']} and {other['id']}"
    for edge in spec["edges"]:
        route = [tuple(item) for item in edge["route"]]
        assert route[0] == port_position(nodes[edge["from"]["node"]], edge["from"]["port"])
        assert route[-1] == port_position(nodes[edge["to"]["node"]], edge["to"]["port"])
        assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(route, route[1:]))


def render(spec: dict) -> str:
    canvas, colors = spec["canvas"], spec["style"]["semantic_colors"]
    marker_colors = {
        "spec": "#2F6BFF",
        "verification": "#7667E8",
        "evidence": "#16A3A5",
        "authority": "#D97706",
        "operations": "#238636",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {canvas["width"]} {canvas["height"]}">',
        f'<title id="title">{escape(spec["title"])}</title>',
        f'<desc id="desc">{escape(spec["output"]["alt_text"])}</desc>',
        """<defs>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="4" stdDeviation="7" flood-color="#16324F" flood-opacity="0.09"/></filter>
        <marker id="arrow-spec" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#2F6BFF"/></marker>
        <marker id="arrow-verification" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#7667E8"/></marker>
        <marker id="arrow-evidence" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#16A3A5"/></marker>
        <marker id="arrow-authority" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#D97706"/></marker>
        <marker id="arrow-operations" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#238636"/></marker>
        <style>text{font-family:Inter,Arial,sans-serif;fill:#16324F}.title{font-size:30px;font-weight:750}.subtitle{font-size:16px;fill:#52606D}.group{font-size:14px;font-weight:750;letter-spacing:1.4px;fill:#52606D}.label{font-size:17px;font-weight:700}.note{font-size:13px;fill:#52606D}.edge{font-size:13px;font-weight:650;fill:#52606D;paint-order:stroke;stroke:#F7F9FC;stroke-width:8px}</style>
        </defs>""",
        f'<rect width="100%" height="100%" fill="{canvas["background"]}"/>',
        f'<text x="60" y="58" class="title">{escape(spec["title"])}</text>',
        '<text x="60" y="92" class="subtitle">Evidence measures a claim; an accountable gate interprets it; runtime feedback can reopen the specification.</text>',
    ]
    for group in spec["groups"]:
        bounds = group["bounds"]
        parts.append(
            f'<g filter="url(#shadow)"><rect x="{bounds["x"]}" y="{bounds["y"]}" width="{bounds["width"]}" height="{bounds["height"]}" rx="18" fill="{group["fill"]}" stroke="{group["stroke"]}"/></g>'
            f'<text x="{bounds["x"] + 24}" y="{bounds["y"] + 38}" class="group">{escape(group["label"])}</text>'
        )
    for edge in spec["edges"]:
        points = " ".join(f"{x},{y}" for x, y in edge["route"])
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{marker_colors[edge["kind"]]}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrow-{edge["kind"]})"/>'
        )
        if edge.get("label"):
            x, y = edge["label_position"]
            parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" class="edge">{escape(edge["label"])}</text>')
    for node in spec["nodes"]:
        bounds, palette = node["bounds"], colors[node["type"]]
        x, y = bounds["x"], bounds["y"]
        parts.append(
            f'<g><rect x="{x}" y="{y}" width="{bounds["width"]}" height="{bounds["height"]}" rx="14" fill="{palette["fill"]}" stroke="{palette["stroke"]}" stroke-width="2"/>'
            f'<text x="{x + 20}" y="{y + 42}" class="label">{escape(node["label"][0])}</text>'
            f'<text x="{x + 20}" y="{y + 73}" class="note">{escape(node["subtitle"])}</text></g>'
        )
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
