from __future__ import annotations

import html
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.data_generator import STPDataGenerator

OUTPUT_FILE = ROOT / "frontend" / "visual_gallery.html"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fmt(value: float, digits: int = 1) -> str:
    text = f"{value:.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def svg_wrap(width: int, height: int, inner: str, *, view_box: str | None = None) -> str:
    view_box = view_box or f"0 0 {width} {height}"
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{view_box}" role="img">{inner}</svg>'


def svg_defs() -> str:
    return """
    <defs>
      <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
        <path d="M0,0 L12,6 L0,12 z" fill="#6b7280"></path>
      </marker>
      <linearGradient id="softBlue" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%" stop-color="#dbeafe"></stop>
        <stop offset="100%" stop-color="#eff6ff"></stop>
      </linearGradient>
      <linearGradient id="softGreen" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%" stop-color="#d1fae5"></stop>
        <stop offset="100%" stop-color="#ecfdf5"></stop>
      </linearGradient>
      <linearGradient id="softAmber" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%" stop-color="#fef3c7"></stop>
        <stop offset="100%" stop-color="#fffbeb"></stop>
      </linearGradient>
      <linearGradient id="softRose" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%" stop-color="#fee2e2"></stop>
        <stop offset="100%" stop-color="#fff1f2"></stop>
      </linearGradient>
    </defs>
    """


def section(title: str, subtitle: str, body: str, *, wide: bool = False) -> str:
    return f"""
    <article class="panel {'wide' if wide else ''}">
      <div class="panel-head">
        <h2>{esc(title)}</h2>
        <p>{esc(subtitle)}</p>
      </div>
      {body}
    </article>
    """


def line_chart_svg(
    title: str,
    x_values: list[float],
    series: list[dict[str, object]],
    *,
    x_label: str,
    y_label: str,
    width: int = 1080,
    height: int = 360,
    y_min: float | None = None,
    y_max: float | None = None,
    annotations: list[dict[str, object]] | None = None,
) -> str:
    left, right, top, bottom = 78, 28, 28, 56
    plot_w = width - left - right
    plot_h = height - top - bottom
    flat_values = [value for item in series for value in item["values"]]  # type: ignore[index]
    if y_min is None:
        y_min = min(flat_values)
    if y_max is None:
        y_max = max(flat_values)
    if math.isclose(y_min, y_max):
        y_max = y_min + 1.0

    def x_pos(index: int) -> float:
        if len(x_values) == 1:
            return left + plot_w / 2
        return left + (index / (len(x_values) - 1)) * plot_w

    def y_pos(value: float) -> float:
        return top + (1 - (value - y_min) / (y_max - y_min)) * plot_h

    x_ticks = [0, 4, 8, 12, 16, 20, 24]
    y_ticks = 5
    grid = []
    for i in range(y_ticks + 1):
        y_value = y_min + (i / y_ticks) * (y_max - y_min)
        y = y_pos(y_value)
        grid.append(f'<line x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1" />')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="13" fill="#6b7280">{fmt(y_value, 1)}</text>')

    for tick in x_ticks:
        if tick not in x_values:
            continue
        idx = x_values.index(tick)
        x = x_pos(idx)
        grid.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{height - bottom}" stroke="#f3f4f6" stroke-width="1" />')
        grid.append(f'<text x="{x:.1f}" y="{height - bottom + 24}" text-anchor="middle" font-size="13" fill="#6b7280">{fmt(tick, 0)}</text>')

    paths = []
    legend = []
    for item in series:
        values = [float(value) for value in item["values"]]  # type: ignore[index]
        color = str(item.get("color", "#2563eb"))
        label = str(item.get("label", "Series"))
        dash = item.get("dash")
        widths = item.get("stroke_width", 2.5)
        points = " ".join(f"{x_pos(index):.1f},{y_pos(value):.1f}" for index, value in enumerate(values))
        paths.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="{widths}" '
            f'points="{points}" stroke-linecap="round" stroke-linejoin="round"'
            + (f' stroke-dasharray="{dash}"' if dash else "")
            + "></polyline>"
        )
        marker_radius = item.get("marker_radius", 3.5)
        for index, value in enumerate(values):
            radius = marker_radius if isinstance(marker_radius, (int, float)) else 3.5
            if item.get("highlight_index") == index:
                radius = item.get("highlight_radius", 7)
            if item.get("show_points", True):
                paths.append(
                    f'<circle cx="{x_pos(index):.1f}" cy="{y_pos(value):.1f}" r="{radius}" fill="{color}" stroke="#ffffff" stroke-width="1.8"></circle>'
                )
        legend.append(
            f'<g transform="translate(0, 0)"><line x1="0" y1="0" x2="28" y2="0" stroke="{color}" stroke-width="3" '
            + (f'stroke-dasharray="{dash}"' if dash else "")
            + f' stroke-linecap="round"></line><text x="38" y="5" font-size="13" fill="#374151">{esc(label)}</text></g>'
        )

    annotation_nodes = []
    for item in annotations or []:
        idx = int(item["index"])
        value = float(item["value"])
        label = str(item["label"])
        color = str(item.get("color", "#dc2626"))
        x = x_pos(idx)
        y = y_pos(value)
        annotation_nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}" stroke="#fff" stroke-width="2"></circle>')
        annotation_nodes.append(f'<line x1="{x:.1f}" y1="{y - 9:.1f}" x2="{x + 76:.1f}" y2="{y - 34:.1f}" stroke="{color}" stroke-width="1.5" marker-end="url(#arrow)"></line>')
        annotation_nodes.append(f'<rect x="{x + 70:.1f}" y="{y - 54:.1f}" rx="8" ry="8" width="170" height="28" fill="#fff7ed" stroke="#f59e0b" />')
        annotation_nodes.append(f'<text x="{x + 155:.1f}" y="{y - 35.5:.1f}" text-anchor="middle" font-size="12.5" fill="#9a3412">{esc(label)}</text>')

    legend_x = width - right - 270
    legend_y = top + 4
    legend_svg = [f'<g transform="translate({legend_x},{legend_y})">']
    for i, item in enumerate(legend):
        legend_svg.append(f'<g transform="translate(0,{i * 20})">{item}</g>')
    legend_svg.append('</g>')

    return svg_wrap(
        width,
        height,
        svg_defs()
        + f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"></rect>'
        + f'<text x="{left}" y="20" font-size="16" fill="#111827" font-weight="600">{esc(title)}</text>'
        + ''.join(grid)
        + ''.join(paths)
        + ''.join(annotation_nodes)
        + ''.join(legend_svg)
        + f'<text x="{left + plot_w / 2:.1f}" y="{height - 14}" text-anchor="middle" font-size="13" fill="#6b7280">{esc(x_label)}</text>'
        + f'<text x="20" y="{top + plot_h / 2:.1f}" transform="rotate(-90 20 {top + plot_h / 2:.1f})" text-anchor="middle" font-size="13" fill="#6b7280">{esc(y_label)}</text>'
    )


def flow_diagram_svg(
    title: str,
    nodes: list[dict[str, str]],
    *,
    width: int = 1180,
    height: int = 280,
    subtitle: str | None = None,
    special: dict[int, str] | None = None,
) -> str:
    node_w, node_h = 150, 88
    left_margin = 34
    top = 88
    gap = (width - 2 * left_margin - len(nodes) * node_w) / max(len(nodes) - 1, 1)
    elements = [f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"></rect>']
    elements.append(f'<text x="{left_margin}" y="24" font-size="16" fill="#111827" font-weight="600">{esc(title)}</text>')
    if subtitle:
        elements.append(f'<text x="{left_margin}" y="46" font-size="12.5" fill="#6b7280">{esc(subtitle)}</text>')
    for index in range(len(nodes) - 1):
        x1 = left_margin + index * (node_w + gap) + node_w
        x2 = left_margin + (index + 1) * (node_w + gap)
        y = top + node_h / 2
        elements.append(f'<line x1="{x1:.1f}" x2="{x2:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="#94a3b8" stroke-width="2.2" marker-end="url(#arrow)"></line>')
    for index, node in enumerate(nodes):
        x = left_margin + index * (node_w + gap)
        y = top
        fill = node.get("fill", "#f8fafc")
        stroke = node.get("stroke", "#cbd5e1")
        kind = node.get("kind", "box")
        elements.append(f'<g transform="translate({x:.1f},{y:.1f})">')
        elements.append(f'<rect x="0" y="0" width="{node_w}" height="{node_h}" rx="14" ry="14" fill="{fill}" stroke="{stroke}" stroke-width="1.5"></rect>')
        if kind == "tank":
            elements.append(f'<path d="M22 {node_h - 20} C 40 {node_h - 30}, 56 {node_h - 10}, 76 {node_h - 20} S 112 {node_h - 30}, 128 {node_h - 20}" fill="none" stroke="#60a5fa" stroke-width="2"></path>')
            elements.append(f'<circle cx="28" cy="22" r="4" fill="#93c5fd"></circle><circle cx="38" cy="15" r="3" fill="#bfdbfe"></circle>')
        elif kind == "screen":
            for bar in (24, 42, 60, 78):
                elements.append(f'<line x1="{bar}" y1="20" x2="{bar}" y2="{node_h - 18}" stroke="#64748b" stroke-width="2"></line>')
        elif kind == "pipe":
            elements.append(f'<rect x="20" y="34" width="110" height="18" rx="9" fill="#dbeafe" stroke="#93c5fd"></rect>')
        elif kind == "disinfection":
            elements.append(f'<path d="M56 20 L76 44 L56 68 L36 44 Z" fill="#fef3c7" stroke="#f59e0b" stroke-width="1.5"></path>')
        elif kind == "outlet":
            elements.append(f'<path d="M18 44 H92" stroke="#2563eb" stroke-width="3"></path><path d="M88 30 L112 44 L88 58" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>')
        if index in (special or {}):
            note = esc((special or {})[index])
            elements.append(f'<rect x="14" y="60" width="122" height="18" rx="9" fill="#eff6ff" stroke="#bfdbfe"></rect><text x="75" y="73" text-anchor="middle" font-size="11.5" fill="#1d4ed8">{note}</text>')
        elements.append(f'<text x="{node_w / 2}" y="56" text-anchor="middle" font-size="15" fill="#111827" font-weight="600">{esc(node["label"])}</text>')
        if node.get("sub"):
            elements.append(f'<text x="{node_w / 2}" y="73" text-anchor="middle" font-size="11.5" fill="#6b7280">{esc(node["sub"])}</text>')
        elements.append('</g>')
    elements.append(f'<text x="{left_margin}" y="{height - 18}" font-size="12.5" fill="#6b7280">Flow direction: left to right</text>')
    return svg_wrap(width, height, svg_defs() + ''.join(elements))


def attention_svg() -> str:
    width, height = 1100, 320
    left, base_y = 40, 180
    seq = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
    weights = [0.08, 0.10, 0.14, 0.22, 0.18, 0.12, 0.10, 0.06]
    box_w, box_h = 88, 48
    gap = 18
    output_x = 860
    inner = [f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"></rect>']
    inner.append(f'<text x="{left}" y="24" font-size="16" fill="#111827" font-weight="600">Attention Mechanism</text>')
    inner.append(f'<text x="{left}" y="42" font-size="12.5" fill="#6b7280">Heat intensity represents attention weight on each input token.</text>')
    for idx, (token, weight) in enumerate(zip(seq, weights)):
        x = left + idx * (box_w + gap)
        fill_alpha = 0.20 + weight * 2.2
        inner.append(f'<line x1="{x + box_w / 2:.1f}" y1="{base_y - 58}" x2="{output_x}" y2="{base_y + 6}" stroke="#cbd5e1" stroke-width="1.5" opacity="0.75"></line>')
        inner.append(f'<rect x="{x}" y="{base_y}" width="{box_w}" height="{box_h}" rx="10" fill="rgba(59,130,246,{fill_alpha:.2f})" stroke="#93c5fd"></rect>')
        inner.append(f'<rect x="{x}" y="{base_y - weight * 140:.1f}" width="{box_w}" height="{weight * 140:.1f}" rx="10" fill="#2563eb" opacity="{clamp(0.18 + weight * 2.4, 0.18, 0.95):.2f}"></rect>')
        inner.append(f'<text x="{x + box_w / 2}" y="{base_y + 30}" text-anchor="middle" font-size="14" fill="#0f172a" font-weight="600">{token}</text>')
        inner.append(f'<text x="{x + box_w / 2}" y="{base_y - 10}" text-anchor="middle" font-size="12" fill="#1d4ed8">{fmt(weight, 2)}</text>')
    inner.append(f'<rect x="{output_x}" y="120" width="170" height="100" rx="16" fill="#ecfdf5" stroke="#6ee7b7"></rect>')
    inner.append(f'<text x="{output_x + 85}" y="165" text-anchor="middle" font-size="15" fill="#065f46" font-weight="700">Weighted Output</text>')
    inner.append(f'<text x="{output_x + 85}" y="187" text-anchor="middle" font-size="12.5" fill="#047857">Context-aware representation</text>')
    inner.append(f'<line x1="{left + 8}" y1="{base_y + 78}" x2="{output_x}" y2="{170}" stroke="#2563eb" stroke-width="2.2" marker-end="url(#arrow)"></line>')
    inner.append(f'<rect x="{left}" y="248" width="460" height="34" rx="9" fill="#f8fafc" stroke="#e2e8f0"></rect>')
    inner.append(f'<text x="{left + 14}" y="269" font-size="12.5" fill="#475569">Higher attention weight highlights the most important inputs for the current prediction.</text>')
    return svg_wrap(width, height, svg_defs() + ''.join(inner))


def alert_flow_svg() -> str:
    width, height = 1180, 300
    nodes = [
        {"shape": "rect", "label": "Input Data", "fill": "#f8fafc"},
        {"shape": "rect", "label": "Check Threshold", "fill": "#eff6ff"},
        {"shape": "diamond", "label": "Exceeds Limit?", "fill": "#fff7ed"},
        {"shape": "rect", "label": "Generate Alert", "fill": "#fee2e2"},
        {"shape": "rect", "label": "Display to User", "fill": "#ecfdf5"},
    ]
    left_margin = 44
    node_y = 108
    node_w, node_h = 150, 76
    gap = 38
    inner = [f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"></rect>']
    inner.append(f'<text x="{left_margin}" y="28" font-size="16" fill="#111827" font-weight="600">Alert System Workflow</text>')
    inner.append(f'<text x="{left_margin}" y="48" font-size="12.5" fill="#6b7280">Standard flowchart symbols with a decision branch for threshold evaluation.</text>')
    xs = [left_margin + i * (node_w + gap) for i in range(len(nodes))]
    for index in range(len(nodes) - 1):
        start_x = xs[index] + node_w
        end_x = xs[index + 1]
        inner.append(f'<line x1="{start_x}" y1="{node_y + node_h / 2}" x2="{end_x}" y2="{node_y + node_h / 2}" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"></line>')
    for index, node in enumerate(nodes):
        x = xs[index]
        if node["shape"] == "diamond":
            inner.append(f'<polygon points="{x + 75},{node_y} {x + 150},{node_y + 38} {x + 75},{node_y + 76} {x},{node_y + 38}" fill="{node["fill"]}" stroke="#d97706" stroke-width="1.5"></polygon>')
            text_x, text_y = x + 75, node_y + 42
        else:
            inner.append(f'<rect x="{x}" y="{node_y}" width="{node_w}" height="{node_h}" rx="14" fill="{node["fill"]}" stroke="#cbd5e1" stroke-width="1.5"></rect>')
            text_x, text_y = x + 75, node_y + 42
        inner.append(f'<text x="{text_x}" y="{text_y}" text-anchor="middle" font-size="14" fill="#111827" font-weight="600">{esc(node["label"])}</text>')
    inner.append(f'<path d="M {xs[2] + 142} {node_y + 22} C {xs[2] + 188} {node_y - 18}, {xs[3] - 10} {node_y - 14}, {xs[3] + 12} {node_y + 18}" fill="none" stroke="#dc2626" stroke-width="1.8" marker-end="url(#arrow)"></path>')
    inner.append(f'<path d="M {xs[2] + 75} {node_y + 76} C {xs[2] + 75} {node_y + 126}, {xs[4] + 65} {node_y + 130}, {xs[4] + 65} {node_y + 84}" fill="none" stroke="#16a34a" stroke-width="1.8" marker-end="url(#arrow)"></path>')
    inner.append(f'<text x="{xs[2] + 170}" y="{node_y - 10}" font-size="12.5" fill="#dc2626">Yes</text>')
    inner.append(f'<text x="{xs[2] + 52}" y="{node_y + 128}" font-size="12.5" fill="#16a34a">No</text>')
    return svg_wrap(width, height, svg_defs() + ''.join(inner))


def stacked_blocks_svg(title: str, labels: list[str], *, width: int = 1180, height: int = 250) -> str:
    left_margin = 54
    top = 92
    block_w = (width - 2 * left_margin - (len(labels) - 1) * 24) / len(labels)
    colors = ["#eff6ff", "#ecfeff", "#f8fafc", "#fff7ed", "#fef2f2", "#ecfdf5"]
    inner = [f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"></rect>']
    inner.append(f'<text x="{left_margin}" y="26" font-size="16" fill="#111827" font-weight="600">{esc(title)}</text>')
    inner.append(f'<text x="{left_margin}" y="46" font-size="12.5" fill="#6b7280">Left-to-right pipeline with labeled data flow.</text>')
    for index, label in enumerate(labels):
        x = left_margin + index * (block_w + 24)
        color = colors[index % len(colors)]
        inner.append(f'<rect x="{x:.1f}" y="{top}" width="{block_w:.1f}" height="84" rx="14" fill="{color}" stroke="#cbd5e1"></rect>')
        inner.append(f'<text x="{x + block_w / 2:.1f}" y="{top + 44}" text-anchor="middle" font-size="14.5" fill="#111827" font-weight="600">{esc(label)}</text>')
        if index < len(labels) - 1:
            inner.append(f'<line x1="{x + block_w:.1f}" y1="{top + 42}" x2="{x + block_w + 22:.1f}" y2="{top + 42}" stroke="#94a3b8" stroke-width="2.2" marker-end="url(#arrow)"></line>')
    return svg_wrap(width, height, svg_defs() + ''.join(inner))


def attention_heatmap_svg(title: str, labels: list[str], weights: list[float], *, width: int = 1180, height: int = 280) -> str:
    left, top = 58, 72
    box_w, box_h, gap = 118, 62, 12
    inner = [f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"></rect>']
    inner.append(f'<text x="{left}" y="26" font-size="16" fill="#111827" font-weight="600">{esc(title)}</text>')
    inner.append(f'<text x="{left}" y="46" font-size="12.5" fill="#6b7280">Darker cells indicate stronger attention on the corresponding input positions.</text>')
    for index, (label, weight) in enumerate(zip(labels, weights)):
        x = left + index * (box_w + gap)
        opacity = clamp(0.18 + weight * 3.4, 0.18, 0.96)
        inner.append(f'<rect x="{x}" y="{top}" width="{box_w}" height="{box_h}" rx="12" fill="#eff6ff" stroke="#bfdbfe"></rect>')
        inner.append(f'<rect x="{x}" y="{top}" width="{box_w}" height="{box_h}" rx="12" fill="#1d4ed8" opacity="{opacity:.2f}"></rect>')
        inner.append(f'<text x="{x + box_w / 2}" y="{top + 30}" text-anchor="middle" font-size="14" fill="#0f172a" font-weight="600">{esc(label)}</text>')
        inner.append(f'<text x="{x + box_w / 2}" y="{top + 48}" text-anchor="middle" font-size="12" fill="#1d4ed8">{fmt(weight, 2)}</text>')
    inner.append(f'<line x1="{left}" y1="{top + box_h + 34}" x2="{left + len(labels) * (box_w + gap) - gap}" y2="{top + box_h + 34}" stroke="#cbd5e1" stroke-width="2" marker-end="url(#arrow)"></line>')
    inner.append(f'<rect x="{left}" y="{top + box_h + 48}" width="360" height="40" rx="10" fill="#f8fafc" stroke="#e2e8f0"></rect>')
    inner.append(f'<text x="{left + 18}" y="{top + box_h + 73}" font-size="12.5" fill="#475569">Weighted sum compresses the attended sequence into a focused representation.</text>')
    return svg_wrap(width, height, svg_defs() + ''.join(inner))


def sample_table_html() -> str:
    generator = STPDataGenerator(seed=42)
    rows = generator.generate_day(datetime(2026, 4, 30))
    body_rows = []
    for record in rows:
        body_rows.append(
            "<tr>"
            f"<td>{record.timestamp.strftime('%H:%M')}</td>"
            f"<td>{fmt(record.BOD, 2)}</td>"
            f"<td>{fmt(record.COD, 2)}</td>"
            f"<td>{fmt(record.pH, 2)}</td>"
            f"<td>{fmt(record.DO, 2)}</td>"
            f"<td>{fmt(record.NH3_N, 2)}</td>"
            f"<td>{fmt(record.TP, 2)}</td>"
            "</tr>"
        )
    return f"""
    <div class="table-card">
      <div class="table-head">
        <div>
          <h3>Hourly Wastewater Data</h3>
          <p>24-hour sample table for research and model input validation.</p>
        </div>
        <span class="pill">24 rows</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th><th>BOD</th><th>COD</th><th>pH</th><th>DO</th><th>Ammonia</th><th>TP</th>
            </tr>
          </thead>
          <tbody>{''.join(body_rows)}</tbody>
        </table>
      </div>
    </div>
    """


def dashboard_ui_html() -> str:
    cards = []
    metrics = [("BOD", "22.4 mg/L", "normal"), ("COD", "48.2 mg/L", "normal"), ("DO", "5.9 mg/L", "warning"), ("pH", "7.1", "normal")]
    for label, value, state in metrics:
        cards.append(f'<div class="metric-card {state}"><span>{esc(label)}</span><strong>{esc(value)}</strong><small>Current reading</small></div>')
    forecast_cards = []
    for hour, bod, status in [("08:00", "26", "warn"), ("12:00", "21", "ok"), ("16:00", "19", "ok"), ("20:00", "28", "warn")]:
        forecast_cards.append(f'<div class="forecast-card {status}"><span>{hour}</span><strong>{bod}</strong><small>BOD mg/L</small></div>')
    return f"""
    <div class="ui-shell dashboard-preview">
      <div class="ui-sidebar">
        <div class="brand-chip">STP</div>
        <div class="nav-item active">Overview</div>
        <div class="nav-item">Forecast</div>
        <div class="nav-item">Alerts</div>
        <div class="nav-item">Reports</div>
      </div>
      <div class="ui-main">
        <div class="ui-topbar">
          <div>
            <h3>Smart STP Monitoring Dashboard</h3>
            <p>Minimal, research-oriented monitoring UI.</p>
          </div>
          <div class="status-chip">Operational</div>
        </div>
        <div class="metric-grid">{''.join(cards)}</div>
        <div class="panel-grid">
          <div class="chart-panel">
            <h4>Line Charts</h4>
            <div class="mini-chart"></div>
            <div class="mini-chart alt"></div>
          </div>
          <div class="forecast-panel">
            <h4>Hourly Forecast</h4>
            <div class="forecast-grid">{''.join(forecast_cards)}</div>
          </div>
        </div>
        <div class="alert-panel">
          <h4>Alerts</h4>
          <div class="alert-row warning"><strong>Warning</strong><span>DO slightly below target at 05:00</span></div>
          <div class="alert-row critical"><strong>Critical</strong><span>BOD spike detected at 14:00</span></div>
        </div>
      </div>
    </div>
    """


def alert_ui_html() -> str:
    return """
    <div class="ui-shell alert-preview">
      <div class="notification warning">
        <span>Warning Alert</span>
        <strong>DO trending below safe range</strong>
        <p>05:00 • Review aeration settings and check blower pressure.</p>
      </div>
      <div class="notification critical">
        <span>Critical Alert</span>
        <strong>Organic load spike detected</strong>
        <p>14:00 • BOD and COD exceed threshold; operator intervention required.</p>
      </div>
    </div>
    """


def login_ui_html() -> str:
    return """
    <div class="ui-shell login-preview">
      <div class="login-hero">
        <div class="brand-chip">S</div>
        <h3>SPECTRUM DYE WORKS</h3>
        <p>Clean login page for operators and administrators.</p>
      </div>
      <form class="login-form">
        <label>Username</label>
        <input type="text" value="operator" />
        <label>Password</label>
        <input type="password" value="••••••••" />
        <button type="button">Login</button>
      </form>
    </div>
    """


def real_vs_predicted_data() -> tuple[list[float], list[float], list[float]]:
    x = list(range(0, 25))
    actual = [42 + 2.5 * math.sin((hour / 24) * 2 * math.pi) + 0.5 * math.cos(hour / 3) for hour in x]
    predicted = [value + (0.8 if hour > 12 else -0.4) for hour, value in enumerate(actual)]
    return x, actual, predicted


def training_accuracy_data() -> tuple[list[float], list[float], list[float]]:
    epochs = list(range(1, 26))
    train = [0.61 + 0.015 * epoch + 0.03 * math.tanh((epoch - 6) / 6) for epoch in epochs]
    val = [0.58 + 0.014 * epoch + 0.018 * math.tanh((epoch - 8) / 7) - 0.004 * max(0, epoch - 18) for epoch in epochs]
    return epochs, train, val


def build_gallery() -> str:
    flow_nodes = [
        {"label": "Inlet Wastewater", "sub": "Raw influent", "kind": "pipe", "fill": "#f8fafc"},
        {"label": "Screening", "sub": "Solids removal", "kind": "screen", "fill": "#eff6ff"},
        {"label": "Primary Sedimentation", "sub": "Settling tank", "kind": "tank", "fill": "#f8fafc"},
        {"label": "Aeration Tank", "sub": "Biological oxidation", "kind": "tank", "fill": "#ecfdf5"},
        {"label": "Secondary Clarifier", "sub": "Final settling", "kind": "tank", "fill": "#f8fafc"},
        {"label": "Disinfection", "sub": "Contact tank", "kind": "disinfection", "fill": "#fff7ed"},
        {"label": "Treated Water Outlet", "sub": "Final effluent", "kind": "outlet", "fill": "#f8fafc"},
    ]
    bod_cod_do_x = list(range(0, 25))
    bod_cod_do_svg = line_chart_svg(
        "BOD - COD - DO Relation",
        bod_cod_do_x,
        [
            {"label": "BOD", "values": [36 - 1.0 * h + 2.2 * math.exp(-h / 5) for h in bod_cod_do_x], "color": "#2563eb", "show_points": False},
            {"label": "COD", "values": [58 - 0.85 * h + 1.8 * math.exp(-h / 7) for h in bod_cod_do_x], "color": "#059669", "show_points": False},
            {"label": "DO", "values": [3.0 + 0.22 * h + 0.4 * math.sin(h / 4) for h in bod_cod_do_x], "color": "#d97706", "show_points": False},
        ],
        x_label="Time (hours)",
        y_label="Concentration",
        y_min=0,
        y_max=60,
    )

    spike_hour = 17
    spike_values = [18 + 1.5 * math.sin((hour / 24) * 2 * math.pi) + (4 if 6 <= hour <= 10 else 0) + (2 if 12 <= hour <= 16 else 0) + (14 if hour == spike_hour else 0) for hour in bod_cod_do_x]
    daily_spike_svg = line_chart_svg(
        "Daily Wastewater Pattern with Spike",
        bod_cod_do_x,
        [{"label": "BOD", "values": spike_values, "color": "#2563eb", "show_points": False}],
        x_label="Time (0-24 hours)",
        y_label="BOD values",
        y_min=8,
        y_max=38,
        annotations=[{"index": spike_hour, "value": spike_values[spike_hour], "label": "Spike", "color": "#dc2626"}],
    )

    anomaly_x = list(range(0, 25))
    anomaly_values = [16 + 1.4 * math.sin((hour / 24) * 2 * math.pi) + (10 if hour == 15 else 0) for hour in anomaly_x]
    spike_visual_svg = line_chart_svg(
        "Spike Visualization",
        anomaly_x,
        [{"label": "BOD", "values": anomaly_values, "color": "#0f766e", "show_points": False}],
        x_label="Time (hours)",
        y_label="BOD",
        y_min=12,
        y_max=30,
        annotations=[{"index": 15, "value": anomaly_values[15], "label": "Abnormal Spike Event", "color": "#dc2626"}],
    )

    real_x, actual, predicted = real_vs_predicted_data()
    real_vs_pred_svg = line_chart_svg(
        "Real vs Predicted Comparison",
        real_x,
        [
            {"label": "Actual", "values": actual, "color": "#2563eb", "show_points": False},
            {"label": "Predicted", "values": predicted, "color": "#dc2626", "dash": "7 5", "show_points": False},
        ],
        x_label="Time",
        y_label="Value",
        y_min=38,
        y_max=48,
    )

    epochs, train_acc, val_acc = training_accuracy_data()
    accuracy_svg = line_chart_svg(
        "Training vs Validation Accuracy",
        epochs,
        [
            {"label": "Training Accuracy", "values": train_acc, "color": "#2563eb", "show_points": False},
            {"label": "Validation Accuracy", "values": val_acc, "color": "#16a34a", "dash": "7 5", "show_points": False},
        ],
        x_label="Epochs",
        y_label="Accuracy",
        y_min=0.55,
        y_max=1.02,
    )

    trend_values = {
        "BOD": [24 + 3 * math.sin(h / 4) + (1.8 if 6 <= h <= 10 else 0) for h in real_x],
        "COD": [44 + 4 * math.sin(h / 4 + 0.5) + (3.0 if 6 <= h <= 10 else 0) for h in real_x],
        "pH": [7.1 + 0.15 * math.sin(h / 6) for h in real_x],
        "DO": [5.2 - 0.6 * math.sin(h / 5) - (0.6 if 6 <= h <= 10 else 0) for h in real_x],
    }
    trend_svg = line_chart_svg(
        "Parameter Trend Graph",
        real_x,
        [
            {"label": "BOD", "values": trend_values["BOD"], "color": "#2563eb", "show_points": False},
            {"label": "COD", "values": trend_values["COD"], "color": "#dc2626", "show_points": False},
            {"label": "pH", "values": trend_values["pH"], "color": "#7c3aed", "show_points": False},
            {"label": "DO", "values": trend_values["DO"], "color": "#059669", "show_points": False},
        ],
        x_label="Time",
        y_label="Trend value",
        y_min=0,
        y_max=55,
    )

    model_pipeline = stacked_blocks_svg(
        "Model Training Pipeline",
        ["Data Collection", "Preprocessing", "Training", "Validation", "Prediction"],
    )

    cnn_lstm_attention = stacked_blocks_svg(
        "CNN-LSTM-Attention Architecture",
        ["Input", "CNN Layers", "LSTM Layers", "Attention Layer", "Dense Output"],
    )

    data_flow = stacked_blocks_svg(
        "Data Flow Diagram",
        ["Data Generator", "Database", "AI Model", "Prediction Output", "Dashboard"],
    )

    system_arch = stacked_blocks_svg(
        "System Architecture",
        ["Data Generator", "Database", "CNN-LSTM-Attention Model", "Backend API", "Web Dashboard"],
    )

    alert_workflow = alert_flow_svg()
    process_flow = flow_diagram_svg(
        "STP Process Flow Diagram",
        flow_nodes,
        subtitle="Clean wastewater treatment sequence with clear directional arrows.",
    )

    attention_mechanism = attention_svg()
    attention_heatmap = attention_heatmap_svg(
        "Attention Weights Visualization",
        ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8"],
        [0.06, 0.09, 0.11, 0.20, 0.19, 0.16, 0.11, 0.08],
    )

    sample_table = sample_table_html()
    dashboard_ui = dashboard_ui_html()
    alert_ui = alert_ui_html()
    login_ui = login_ui_html()

    spike_detection_svg = line_chart_svg(
        "Alert Detection Graph",
        anomaly_x,
        [{"label": "Time Series", "values": anomaly_values, "color": "#7c3aed", "show_points": False}],
        x_label="Time",
        y_label="Value",
        y_min=12,
        y_max=30,
        annotations=[{"index": 15, "value": anomaly_values[15], "label": "Alert Triggered", "color": "#dc2626"}],
    )

    html_sections = [
        section("1. STP Process Flow", "Wastewater treatment sequence", process_flow),
        section("2. BOD-COD-DO Relation Graph", "Scientific line graph for wastewater dynamics", bod_cod_do_svg),
        section("3. System Architecture", "AI-based Smart STP prediction pipeline", system_arch),
        section("4. Data Generator + Daily Spike", "Daily pattern with one abnormal event", daily_spike_svg),
        section("5. Data Flow Diagram", "Core AI prediction flow", data_flow),
        section("6. CNN-LSTM-Attention Model", "Deep learning architecture overview", cnn_lstm_attention),
        section("7. Attention Mechanism", "How the network focuses on important inputs", attention_mechanism, wide=True),
        section("8. Alert System Workflow", "Threshold-driven alert logic", alert_workflow),
        section("9. Sample Data Table", "24 hourly wastewater rows", sample_table, wide=True),
        section("10. Spike Visualization Graph", "Highlighted abnormal spike point", spike_visual_svg),
        section("11. Model Training Pipeline", "Machine learning workflow", model_pipeline),
        section("12. Real vs Predicted Graph", "Actual vs forecast comparison", real_vs_pred_svg),
        section("13. Web Dashboard UI", "Modern monitoring dashboard mockup", dashboard_ui, wide=True),
        section("14. Alert UI", "Warning and critical notification cards", alert_ui, wide=True),
        section("15. Login Page", "Minimal sign-in screen", login_ui, wide=True),
        section("16. Accuracy Graph", "Training and validation accuracy across epochs", accuracy_svg),
        section("17. Parameter Trend Graph", "Multi-line operational trend chart", trend_svg),
        section("18. Alert Detection Graph", "Anomaly-focused time series", spike_detection_svg),
        section("7b. Attention Heatmap", "Complementary weight view", attention_heatmap, wide=True),
    ]

    css = """
    :root {
      --bg: #f4f7fb;
      --panel: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: #dbe3ee;
      --shadow: 0 22px 54px rgba(15, 23, 42, 0.06);
      --accent: #2563eb;
      --green: #16a34a;
      --amber: #d97706;
      --red: #dc2626;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Inter", "Segoe UI", Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 24rem),
        radial-gradient(circle at bottom right, rgba(22, 163, 74, 0.08), transparent 24rem),
        var(--bg);
    }
    .wrap { width: min(1500px, calc(100% - 32px)); margin: 24px auto 40px; }
    .hero {
      padding: 22px 24px;
      background: rgba(255,255,255,0.84);
      border: 1px solid rgba(219, 227, 238, 0.86);
      border-radius: 22px;
      box-shadow: var(--shadow);
      margin-bottom: 22px;
      backdrop-filter: blur(10px);
    }
    .hero h1 { margin: 0 0 8px; font-size: 30px; }
    .hero p { margin: 0; color: var(--muted); max-width: 950px; line-height: 1.55; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 18px; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
      overflow: hidden;
      padding: 18px;
    }
    .panel.wide { grid-column: 1 / -1; }
    .panel-head { margin-bottom: 10px; }
    .panel-head h2 { margin: 0 0 4px; font-size: 18px; }
    .panel-head p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.45; }
    svg { width: 100%; height: auto; display: block; }
    .table-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: #fff;
    }
    .table-head {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .table-head h3 { margin: 0 0 4px; font-size: 18px; }
    .table-head p { margin: 0; color: var(--muted); font-size: 13px; }
    .pill {
      display: inline-flex; align-items: center; justify-content: center;
      padding: 8px 12px; border-radius: 999px; background: #eff6ff; color: var(--accent);
      font-size: 12px; font-weight: 700; border: 1px solid #bfdbfe;
    }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 760px; }
    th, td { padding: 11px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; font-size: 13px; white-space: nowrap; }
    th { background: #f8fafc; color: #334155; font-weight: 700; }
    .ui-shell {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      padding: 16px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
    }
    .dashboard-preview { display: grid; grid-template-columns: 180px 1fr; gap: 14px; }
    .ui-sidebar {
      border: 1px solid #dbe3ee; border-radius: 16px; background: #f8fafc; padding: 14px; display: grid; align-content: start; gap: 10px;
    }
    .brand-chip {
      width: 52px; height: 52px; border-radius: 18px; display: grid; place-items: center;
      background: #e0efff; color: var(--accent); font-weight: 800; font-size: 18px;
    }
    .nav-item { padding: 10px 12px; border-radius: 12px; background: #fff; border: 1px solid #e5edf8; color: #334155; font-size: 13px; }
    .nav-item.active { background: #eff6ff; border-color: #bfdbfe; color: var(--accent); font-weight: 700; }
    .ui-main { display: grid; gap: 14px; }
    .ui-topbar { display: flex; justify-content: space-between; align-items: center; gap: 14px; }
    .ui-topbar h3, .forecast-panel h4, .chart-panel h4, .alert-panel h4 { margin: 0 0 4px; }
    .ui-topbar p { margin: 0; color: var(--muted); font-size: 13px; }
    .status-chip { padding: 8px 12px; border-radius: 999px; background: #ecfdf5; color: var(--green); font-weight: 700; border: 1px solid #bbf7d0; }
    .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    .metric-card, .forecast-card, .notification, .alert-row {
      border: 1px solid #e5edf8; border-radius: 16px; background: #fff; padding: 14px; box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }
    .metric-card span, .forecast-card span, .notification span { color: var(--muted); font-size: 12px; display: block; }
    .metric-card strong, .forecast-card strong, .notification strong { display: block; margin-top: 8px; font-size: 24px; }
    .metric-card small, .forecast-card small { color: var(--muted); }
    .metric-card.warning strong { color: var(--amber); }
    .metric-card.normal strong { color: var(--green); }
    .panel-grid { display: grid; grid-template-columns: 1.15fr 0.95fr; gap: 12px; }
    .chart-panel, .forecast-panel, .alert-panel { border: 1px solid #e5edf8; border-radius: 16px; background: #fff; padding: 14px; }
    .mini-chart {
      height: 120px; border-radius: 16px; background: linear-gradient(135deg, rgba(37,99,235,0.12), rgba(255,255,255,0.85));
      border: 1px dashed #bfdbfe; margin-top: 10px;
      position: relative; overflow: hidden;
    }
    .mini-chart::after {
      content: ""; position: absolute; inset: 28px 16px 22px 16px; border-left: 2px solid #cbd5e1; border-bottom: 2px solid #cbd5e1;
      background: linear-gradient(180deg, transparent 48%, rgba(37,99,235,0.08) 48%, rgba(37,99,235,0.08) 52%, transparent 52%);
    }
    .mini-chart.alt { background: linear-gradient(135deg, rgba(22,163,74,0.12), rgba(255,255,255,0.85)); }
    .forecast-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px; }
    .forecast-card span { display: inline-block; }
    .forecast-card.ok strong { color: var(--green); }
    .forecast-card.warn strong { color: var(--amber); }
    .alert-panel { display: grid; gap: 10px; }
    .alert-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
    .alert-row.warning { border-left: 5px solid var(--amber); }
    .alert-row.critical { border-left: 5px solid var(--red); }
    .notification { max-width: 520px; }
    .notification.warning { border-left: 5px solid var(--amber); }
    .notification.critical { border-left: 5px solid var(--red); }
    .alert-preview { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    .login-preview { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: stretch; }
    .login-hero { border: 1px solid #dbe3ee; border-radius: 16px; padding: 24px; background: linear-gradient(160deg, #eff6ff, #ffffff); }
    .login-hero h3 { margin: 14px 0 8px; font-size: 24px; }
    .login-hero p { margin: 0; color: var(--muted); }
    .login-form { border: 1px solid #dbe3ee; border-radius: 16px; padding: 24px; background: #fff; display: grid; gap: 10px; align-content: center; }
    .login-form label { font-size: 12px; color: var(--muted); font-weight: 600; }
    .login-form input {
      width: 100%; padding: 12px 14px; border: 1px solid #dbe3ee; border-radius: 12px; background: #f8fafc; font: inherit;
    }
    .login-form button {
      margin-top: 6px; padding: 12px 14px; border: 0; border-radius: 12px; background: var(--accent); color: #fff; font-weight: 700;
    }
    @media (max-width: 960px) {
      .grid { grid-template-columns: 1fr; }
      .dashboard-preview, .login-preview, .panel-grid, .metric-grid { grid-template-columns: 1fr; }
      .ui-sidebar { grid-template-columns: repeat(2, 1fr); }
    }
    """

    html_page = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>STP Visual Gallery</title>
      <style>{css}</style>
    </head>
    <body>
      <main class="wrap">
        <section class="hero">
          <h1>STP Visual Gallery</h1>
          <p>A single reproducible asset pack for the wastewater treatment project: process flow, scientific graphs, AI architecture, alert workflows, and dashboard/login UI mockups.</p>
        </section>
        <section class="grid">
          {''.join(html_sections)}
        </section>
      </main>
    </body>
    </html>
    """
    return html_page


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(build_gallery(), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()