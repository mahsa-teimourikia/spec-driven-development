"""Validate the Course 19 layout specification and render an accessible SVG."""

from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / "bugfix-workflow-spec.json"
OUTPUT = HERE / "bugfix-workflow.svg"


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
    for index, left in enumerate(nodes.values()):
        a = left["bounds"]
        if min(a.values()) < 0 or a["x"] + a["width"] > width or a["y"] + a["height"] > height:
            raise ValueError(f"invalid bounds: {left['id']}")
        for right in list(nodes.values())[index + 1:]:
            b = right["bounds"]
            if a["x"] < b["x"] + b["width"] and a["x"] + a["width"] > b["x"] and a["y"] < b["y"] + b["height"] and a["y"] + a["height"] > b["y"]:
                raise ValueError(f"overlap: {left['id']} / {right['id']}")
    seen: set[str] = set()
    for edge in spec["edges"]:
        if edge["id"] in seen:
            raise ValueError(f"duplicate edge: {edge['id']}")
        seen.add(edge["id"])
        route = [tuple(point) for point in edge["route"]]
        start = port(nodes[edge["from"]["node"]], edge["from"]["port"])
        end = port(nodes[edge["to"]["node"]], edge["to"]["port"])
        if route[0] != start or route[-1] != end:
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
        '<text x="50" y="66" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="700">A proportional, evidence-bound bug fix</text>',
        '<text x="50" y="104" fill="#52606D" font-family="Inter, Arial, sans-serif" font-size="18">Risk selects the workflow. Evidence—not an agent claim—establishes review eligibility.</text>',
    ]
    for node in spec["nodes"]:
        b, color = node["bounds"], colors[node["type"]]
        result.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="14" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="3"/>')
        x = b["x"] + b["width"] / 2
        first_y = b["y"] + b["height"] / 2 - (len(node["label_lines"]) - 1) * 15
        for index, label in enumerate(node["label_lines"]):
            result.append(f'<text x="{x}" y="{first_y + index * 30}" text-anchor="middle" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="{17 if index == 0 else 15}" font-weight="{700 if index == 0 else 500}">{html.escape(label)}</text>')
    for edge in spec["edges"]:
        points = " ".join(f"{x},{y}" for x, y in edge["route"])
        color = "#087F7B" if edge["kind"] == "feedback" else "#52606D"
        dash = ' stroke-dasharray="8 7"' if edge["kind"] == "feedback" else ""
        result.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" marker-end="url(#arrow)"{dash}/>')
        if edge.get("label"):
            result.append(f'<text x="970" y="548" text-anchor="middle" fill="{color}" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="650">{html.escape(edge["label"])}</text>')
    result.append('<text x="835" y="615" text-anchor="middle" fill="#52606D" font-family="Inter, Arial, sans-serif" font-size="15">Merge and deployment remain separate trusted-authority decisions.</text>')
    result.append("</svg>")
    return "\n".join(result) + "\n"


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    validate(spec)
    OUTPUT.write_text(render(spec), encoding="utf-8")
    print(f"rendered {OUTPUT.name}")


if __name__ == "__main__":
    main()
