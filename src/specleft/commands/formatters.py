"""Formatting helpers for CLI output."""

from __future__ import annotations

from specleft.schema import ExecutionTime


def format_status_marker(status: str) -> str:
    if status == "implemented":
        return "✓"
    if status == "skipped":
        return "⚠"
    return "✗"


def format_coverage_percent(implemented: int, total: int) -> float | None:
    if total == 0:
        return None
    return round((implemented / total) * 100, 1)


def format_execution_time_value(execution_time: str | ExecutionTime) -> str:
    value = (
        execution_time.value
        if isinstance(execution_time, ExecutionTime)
        else execution_time
    )
    return value.capitalize()


def badge_color(coverage: float | None) -> str:
    if coverage is None:
        return "#9f9f9f"
    if coverage >= 80:
        return "#4cce5e"
    if coverage >= 60:
        return "#f0c648"
    return "#e05d44"


def render_badge_svg(label: str, message: str, color: str) -> str:
    def _text_width(text: str) -> int:
        return max(1, len(text)) * 7

    label_width = _text_width(label) + 10
    message_width = _text_width(message) + 10
    total_width = label_width + message_width
    label_x = label_width / 2
    message_x = label_width + message_width / 2
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="'
        f'{total_width}" height="20" role="img" aria-label="{label}: {message}">'
        '<linearGradient id="s" x2="0" y2="100%">'
        '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/>'
        "</linearGradient>"
        f'<rect width="{label_width}" height="20" fill="#555"/>'
        f'<rect x="{label_width}" width="{message_width}" height="20" fill="{color}"/>'
        '<rect width="' + str(total_width) + '" height="20" fill="url(#s)"/>'
        f'<g fill="#fff" text-anchor="middle" font-family="Verdana" font-size="11">'
        f'<text x="{label_x}" y="14">{label}</text>'
        f'<text x="{message_x}" y="14">{message}</text>'
        "</g>"
        "</svg>"
    )
