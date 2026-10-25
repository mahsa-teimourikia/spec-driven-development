"""Validate the Course 18 layout specification and render an accessible SVG."""

from __future__ import annotations

import html
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = HERE / "brownfield-transition-spec.json"
OUTPUT = HERE / "brownfield-transition.svg"


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
    nodes = {node["id"]: node for node in spec["nodes"]}
    if len(nodes) != len(spec["nodes"]):
        raise ValueError("duplicate node id")
    items = list(nodes.values())
    for node in items:
        bounds = node["bounds"]
        if min(bounds["x"], bounds["y"], bounds["width"], bounds["height"]) < 0:
            raise ValueError(f"invalid node bounds: {node['id']}")
        if bounds["x"] + bounds["width"] > width or bounds["y"] + bounds["height"] > height:
            raise ValueError(f"node outside canvas: {node['id']}")
    for index, left in enumerate(items):
        a = left["bounds"]
        for right in items[index + 1 :]:
            b = right["bounds"]
            overlaps = (
                a["x"] < b["x"] + b["width"]
                and a["x"] + a["width"] > b["x"]
                and a["y"] < b["y"] + b["height"]
                and a["y"] + a["height"] > b["y"]
            )
            if overlaps:
                raise ValueError(f"overlap: {left['id']} / {right['id']}")
    edge_ids: set[str] = set()
    for edge in spec["edges"]:
        if edge["id"] in edge_ids:
            raise ValueError(f"duplicate edge: {edge['id']}")
        edge_ids.add(edge["id"])
        route = [tuple(point) for point in edge["route"]]
        start = port(nodes[edge["from"]["node"]], edge["from"]["port"])
        end = port(nodes[edge["to"]["node"]], edge["to"]["port"])
        if any(abs(a - b) > 0.001 for a, b in zip(route[0], start)) or any(abs(a - b) > 0.001 for a, b in zip(route[-1], end)):
            raise ValueError(f"detached edge: {edge['id']}")


def render(spec: dict) -> str:
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    colors = spec["style"]["semantic_colors"]
    result = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(spec["title"])}</title>',
        f'<desc id="desc">{html.escape(spec["output"]["alt_text"])}</desc>',
        f'<rect width="{width}" height="{height}" fill="{spec["canvas"]["background"]}"/>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#52606D"/></marker></defs>',
        '<text x="64" y="66" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="700">A governed brownfield transition</text>',
        '<text x="64" y="104" fill="#52606D" font-family="Inter, Arial, sans-serif" font-size="18">Observe current reality, classify it, change only the approved delta, and keep the transition reversible.</text>',
    ]
    for node in spec["nodes"]:
        bounds = node["bounds"]
        color = colors[node["type"]]
        result.append(f'<rect x="{bounds["x"]}" y="{bounds["y"]}" width="{bounds["width"]}" height="{bounds["height"]}" rx="14" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="3"/>')
        x = bounds["x"] + bounds["width"] / 2
        first_y = bounds["y"] + bounds["height"] / 2 - (len(node["label_lines"]) - 1) * 14
        for index, label in enumerate(node["label_lines"]):
            result.append(f'<text x="{x}" y="{first_y + index * 28}" text-anchor="middle" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="{17 if index == 0 else 15}" font-weight="{700 if index == 0 else 500}">{html.escape(label)}</text>')
    stroke = {"source": "#52606D", "primary": "#52606D", "feedback": "#087F7B", "authority": "#D97706"}
    for edge in spec["edges"]:
        points = " ".join(f"{x},{y}" for x, y in edge["route"])
        dash = ' stroke-dasharray="8 7"' if edge["kind"] in {"feedback", "authority"} else ""
        result.append(f'<polyline points="{points}" fill="none" stroke="{stroke[edge["kind"]]}" stroke-width="3" stroke-linejoin="round" marker-end="url(#arrow)"{dash}/>')
        if edge.get("label"):
            if edge["id"] == "feedback":
                x, y = 920, 558
            else:
                x, y = 1558, 555
            result.append(f'<text x="{x}" y="{y}" text-anchor="middle" fill="{stroke[edge["kind"]]}" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="650">{html.escape(edge["label"])}</text>')
    result.append("</svg>")
    return "\n".join(result) + "\n"


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    validate(spec)
    OUTPUT.write_text(render(spec), encoding="utf-8")
    print(f"rendered {OUTPUT.name}")


if __name__ == "__main__":
    main()
