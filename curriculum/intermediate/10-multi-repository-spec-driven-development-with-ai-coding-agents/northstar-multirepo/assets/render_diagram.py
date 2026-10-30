"""Validate and render the Course 20 multi-repository coordination diagram."""

from __future__ import annotations

import html
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = HERE / "multirepo-control-plane-spec.json"
OUTPUT = HERE / "multirepo-control-plane.svg"
COLORS = {
    "control": ("#FFF1DF", "#D97706"),
    "contract": ("#EAF1FF", "#2F6BFF"),
    "agent": ("#F0EEFF", "#7667E8"),
    "evidence": ("#E5F7F6", "#087F7B"),
    "review": ("#E5F7F6", "#087F7B"),
}


def validate(spec: dict[str, object]) -> None:
    nodes = {node["id"]: node for node in spec["nodes"]}
    if len(nodes) != len(spec["nodes"]):
        raise ValueError("duplicate node id")
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    for index, left in enumerate(nodes.values()):
        if left["x"] < 0 or left["y"] < 0 or left["x"] + left["w"] > width or left["y"] + left["h"] > height:
            raise ValueError(f"node outside canvas: {left['id']}")
        for right in list(nodes.values())[index + 1:]:
            overlap = (
                left["x"] < right["x"] + right["w"]
                and left["x"] + left["w"] > right["x"]
                and left["y"] < right["y"] + right["h"]
                and left["y"] + left["h"] > right["y"]
            )
            if overlap:
                raise ValueError(f"overlap: {left['id']} / {right['id']}")
    for edge in spec["edges"]:
        if edge["from"] not in nodes or edge["to"] not in nodes:
            raise ValueError("edge references unknown node")


def render(spec: dict[str, object]) -> str:
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    nodes = {node["id"]: node for node in spec["nodes"]}
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(spec["title"])}</title>',
        f'<desc id="desc">{html.escape(spec["output"]["alt_text"])}</desc>',
        f'<rect width="{width}" height="{height}" fill="{spec["canvas"]["background"]}"/>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#52606D"/></marker></defs>',
        '<text x="50" y="62" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="32" font-weight="700">Contract-first multi-repository delivery</text>',
        '<text x="50" y="100" fill="#52606D" font-family="Inter, Arial, sans-serif" font-size="18">Parallel work begins only after contract approval; system evidence binds exact repository commits.</text>',
    ]
    for edge in spec["edges"]:
        left, right = nodes[edge["from"]], nodes[edge["to"]]
        x1, y1 = left["x"] + left["w"], left["y"] + left["h"] / 2
        x2, y2 = right["x"], right["y"] + right["h"] / 2
        mid = (x1 + x2) / 2
        output.append(f'<polyline points="{x1},{y1} {mid},{y1} {mid},{y2} {x2},{y2}" fill="none" stroke="#52606D" stroke-width="3" marker-end="url(#arrow)"/>')
    for node in spec["nodes"]:
        fill, stroke = COLORS[node["type"]]
        output.append(f'<rect x="{node["x"]}" y="{node["y"]}" width="{node["w"]}" height="{node["h"]}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
        center = node["x"] + node["w"] / 2
        output.append(f'<text x="{center}" y="{node["y"] + 75}" text-anchor="middle" fill="#16324F" font-family="Inter, Arial, sans-serif" font-size="17" font-weight="700">{html.escape(node["title"])}</text>')
        output.append(f'<text x="{center}" y="{node["y"] + 105}" text-anchor="middle" fill="#52606D" font-family="Inter, Arial, sans-serif" font-size="14">{html.escape(node["subtitle"])}</text>')
    output.append('<text x="840" y="620" text-anchor="middle" fill="#52606D" font-family="Inter, Arial, sans-serif" font-size="16">Merge, deployment, activation, and contract retirement remain separate accountable decisions.</text>')
    output.append("</svg>")
    return "\n".join(output) + "\n"


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    validate(spec)
    OUTPUT.write_text(render(spec), encoding="utf-8")
    print(f"rendered {OUTPUT.name}")


if __name__ == "__main__":
    main()
