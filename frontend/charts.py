"""Plotly charts with readable category, axis and value labels at rest."""

import math
import textwrap

import plotly.graph_objects as go


def figure(spec):
    rows = spec["rows"]
    if not rows:
        return None
    x, y = spec["x"], spec["y"]
    labels = [str(row[x]) for row in rows]
    values = [row[y] for row in rows]
    formatted = [f"{value:,}" for value in values]
    axis_title = "Change in visits" if y == "change" else "Recorded visits"
    left_margin = 64
    chart_height = 360
    if spec["kind"] == "line":
        stride = math.ceil(len(rows) / 12) if len(rows) > 24 else 1
        text = [value if i % stride == 0 or i == len(rows) - 1 else "" for i, value in enumerate(formatted)]
        chart = go.Figure(
            go.Scatter(
                x=labels,
                y=values,
                mode="lines+markers+text",
                text=text,
                textposition="top center",
                textfont={"size": 12, "color": "#234e62"},
                cliponaxis=False,
                marker={"size": 6, "color": "#0d8d98"},
                fill="tozeroy",
                line={"color": "#0d8d98", "width": 2.5},
                fillcolor="rgba(13,141,152,0.07)",
                hovertemplate="%{x}<br>%{y:,} visits<extra></extra>",
            )
        )
        minimum, maximum = min(values), max(values)
        padding = max(1, (maximum - min(0, minimum)) * 0.2)
        chart.update_yaxes(range=[min(0, minimum) - padding * 0.15, maximum + padding], title=axis_title)
        chart.update_xaxes(nticks=7)
    else:
        chart = go.Figure(
            go.Bar(
                y=labels,
                x=values,
                orientation="h",
                marker_color="#159ba5",
                text=formatted,
                textposition="outside",
                cliponaxis=False,
                textfont={"size": 12, "color": "#234e62"},
                hovertemplate="%{y}<br>%{x:,} visits<extra></extra>",
            )
        )
        label_lines = [textwrap.wrap(label, width=20) or [""] for label in labels]
        wrapped = ["<br>".join(lines) for lines in label_lines]
        # Reserve label space before Plotly's first render inside a chat container.
        # Automatic margins alone can leave text outside Streamlit's clipped SVG.
        longest_line = max(len(line) for lines in label_lines for line in lines)
        left_margin = max(88, longest_line * 7 + 24)
        extra_lines = sum(len(lines) - 1 for lines in label_lines)
        chart_height = max(340, len(rows) * 44 + 108) + extra_lines * 16
        chart.update_yaxes(autorange="reversed", tickmode="array", tickvals=labels, ticktext=wrapped)
        minimum, maximum = min(values), max(values)
        padding = max(1, max(abs(minimum), abs(maximum)) * 0.22)
        chart.update_xaxes(
            range=[min(0, minimum) - (padding if minimum < 0 else 0), maximum + padding], title=axis_title
        )
    chart.update_layout(
        autosize=True,
        height=chart_height,
        margin={"l": left_margin, "r": 40, "t": 32, "b": 76, "pad": 4},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Source Sans, Source Sans Pro, Arial, sans-serif", "color": "#294e63", "size": 12},
        showlegend=False,
        dragmode=False,
    )
    chart.update_xaxes(
        showgrid=True,
        gridcolor="#e7eef3",
        zeroline=False,
        showticklabels=True,
        automargin=True,
        tickfont={"size": 11, "color": "#486779"},
    )
    chart.update_yaxes(
        showgrid=spec["kind"] == "line",
        gridcolor="#e7eef3",
        zeroline=False,
        showticklabels=True,
        automargin=True,
        tickfont={"size": 12, "color": "#34576a"},
    )
    return chart
