"""Validate and deterministically render the Course 17 lifecycle SVG."""

from __future__ import annotations

import html
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = HERE / "end-to-end-pdlc-spec.json"
OUTPUT = HERE / "end-to-end-pdlc.svg"


def port(node: dict, name: str) -> tuple[float, float]:
    bounds = node["bounds"]
    item = node["ports"][name]
    offset = item["offset"]
    if item["side"] == "left":
        return bounds["x"], bounds["y"] + bounds["height"] * offset
    if item["side"] == "right":
        return bounds["x"] + bounds["width"], bounds["y"] + bounds["height"] * offset
    if item["side"] == "top":
        return bounds["x"] + bounds["width"] * offset, bounds["y"]
    return bounds["x"] + bounds["width"] * offset, bounds["y"] + bounds["height"]


def validate(spec: dict) -> None:
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    nodes = {item["id"]: item for item in spec["nodes"]}
    if len(nodes) != len(spec["nodes"]):
        raise ValueError("duplicate node id")
    edge_ids = [item["id"] for item in spec["edges"]]
    if len(set(edge_ids)) != len(edge_ids):
        raise ValueError("duplicate edge id")
    for node in nodes.values():
        b = node["bounds"]
        if b["x"] < 0 or b["y"] < 0 or b["x"] + b["width"] > width or b["y"] + b["height"] > height:
            raise ValueError(f"node outside canvas: {node['id']}")
    items = list(nodes.values())
    for index, left in enumerate(items):
        a = left["bounds"]
        for right in items[index + 1:]:
            b = right["bounds"]
            overlap = a["x"] < b["x"] + b["width"] and a["x"] + a["width"] > b["x"] and a["y"] < b["y"] + b["height"] and a["y"] + a["height"] > b["y"]
            if overlap:
                raise ValueError(f"overlapping nodes: {left['id']} and {right['id']}")
    for edge in spec["edges"]:
        source = nodes[edge["from"]["node"]]
        target = nodes[edge["to"]["node"]]
        route = [tuple(point) for point in edge["route"]]
        if route[0] != port(source, edge["from"]["port"]) or route[-1] != port(target, edge["to"]["port"]):
            raise ValueError(f"edge is detached: {edge['id']}")


def render(spec: dict) -> str:
    colors = spec["style"]["semantic_colors"]
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(spec["title"])}</title>',
        f'<desc id="desc">{html.escape(spec["output"]["alt_text"])}</desc>',
        f'<rect width="{width}" height="{height}" fill="{spec["canvas"]["background"]}"/>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#52606D"/></marker></defs>',
        '<text x="64" y="70" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="32" font-weight="700">From approved intent to independently verified implementation</text>',
        '<text x="64" y="106" fill="#52606D" font-family="Inter, Arial, sans-serif" font-size="18">Each state needs its own owner, artifact, evidence, and authorization boundary.</text>',
    ]
    for node in spec["nodes"]:
        b = node["bounds"]
        color = colors[node["type"]]
        lines.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="14" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="3"/>')
        center_x = b["x"] + b["width"] / 2
        first_y = b["y"] + b["height"] / 2 - (len(node["label_lines"]) - 1) * 13
        for index, label in enumerate(node["label_lines"]):
            weight = "700" if index == 0 else "500"
            size = 17 if index == 0 else 15
            lines.append(f'<text x="{center_x}" y="{first_y + index * 28}" text-anchor="middle" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="{size}" font-weight="{weight}">{html.escape(label)}</text>')
    edge_color = {"primary": "#52606D", "feedback": "#16A3A5", "authority": "#F59E42"}
    for edge in spec["edges"]:
        points = " ".join(f"{x},{y}" for x, y in edge["route"])
        color = edge_color[edge["kind"]]
        dash = ' stroke-dasharray="8 7"' if edge["kind"] != "primary" else ""
        lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" marker-end="url(#arrow)"{dash}/>')
        if edge.get("label"):
            if edge["id"] == "evidence-feedback":
                x, y = 660, 430
            else:
                x, y = 1408, 442
            lines.append(f'<text x="{x}" y="{y}" text-anchor="middle" fill="{color}" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="600">{html.escape(edge["label"])}</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    validate(spec)
    OUTPUT.write_text(render(spec), encoding="utf-8")
    print(f"rendered {OUTPUT.name}")


if __name__ == "__main__":
    main()
