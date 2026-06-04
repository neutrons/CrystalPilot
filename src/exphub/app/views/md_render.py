"""Lightweight Markdown to HTML converter for chat bubbles.

Handles common markdown features without external dependencies:
fenced code blocks, inline code, bold, italic, headers, lists, tables.
"""

from __future__ import annotations

import re
from html import escape


def _parse_table(block: str) -> str:
    """Convert a Markdown table block into an HTML <table>.

    Expects lines like::

        | Header 1 | Header 2 |
        |----------|----------|
        | cell 1   | cell 2   |

    The separator row (containing ``---``) determines column alignment:
    ``:---`` = left, ``---:`` = right, ``:---:`` = center.
    """
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return block  # not a valid table

    def _split_row(line: str) -> list[str]:
        # Strip leading/trailing pipes, split on |
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [cell.strip() for cell in line.split("|")]

    def _inline_fmt(text: str) -> str:
        """Apply inline markdown (bold, italic, code) inside a table cell."""
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        return text

    header_cells = _split_row(lines[0])
    sep_cells = _split_row(lines[1])

    # Determine alignment from separator row
    aligns: list[str] = []
    for cell in sep_cells:
        stripped = cell.strip().replace(" ", "")
        if stripped.startswith(":") and stripped.endswith(":"):
            aligns.append("center")
        elif stripped.endswith(":"):
            aligns.append("right")
        else:
            aligns.append("left")

    def _style(col: int) -> str:
        a = aligns[col] if col < len(aligns) else "left"
        return f' style="text-align:{a}"'

    # Build header
    ths = "".join(f"<th{_style(i)}>{_inline_fmt(c)}</th>" for i, c in enumerate(header_cells))
    thead = f"<thead><tr>{ths}</tr></thead>"

    # Build body
    rows_html: list[str] = []
    for line in lines[2:]:
        cells = _split_row(line)
        tds = "".join(f"<td{_style(i)}>{_inline_fmt(c)}</td>" for i, c in enumerate(cells))
        rows_html.append(f"<tr>{tds}</tr>")
    tbody = f"<tbody>{''.join(rows_html)}</tbody>"

    return f"<table>{thead}{tbody}</table>"


def md_to_html(text: str) -> str:
    """Convert basic markdown to HTML for chat bubble display."""
    blocks: list[str] = []

    def _stash_code(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = escape(m.group(2))
        cls = f' class="language-{lang}"' if lang else ""
        blocks.append(f"<pre><code{cls}>{code}</code></pre>")
        return f"\x00CB{len(blocks) - 1}\x00"

    text = re.sub(r"```(\w*)\n(.*?)```", _stash_code, text, flags=re.DOTALL)

    # ── Markdown tables ──
    # Match consecutive lines that start/end with | (header + separator + body).
    # Stash the rendered HTML so later escaping doesn't corrupt it.
    def _stash_table(m: re.Match) -> str:
        table_html = _parse_table(m.group(0))
        blocks.append(table_html)
        return f"\x00CB{len(blocks) - 1}\x00"

    text = re.sub(
        r"(^\|.+\|[ \t]*\n\|[\s:|-]+\|[ \t]*\n(?:\|.+\|[ \t]*\n?)+)",
        _stash_table,
        text,
        flags=re.MULTILINE,
    )

    # Escape remaining HTML
    text = escape(text)

    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic (single *)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Headers
    text = re.sub(r"^### (.+)$", r"<h4>\1</h4>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)

    # Unordered lists (consecutive - or * lines)
    def _ul(m: re.Match) -> str:
        items = re.findall(r"^[-*] (.+)$", m.group(0), re.MULTILINE)
        return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

    text = re.sub(r"(^[-*] .+$\n?)+", _ul, text, flags=re.MULTILINE)

    # Ordered lists
    def _ol(m: re.Match) -> str:
        items = re.findall(r"^\d+\. (.+)$", m.group(0), re.MULTILINE)
        return "<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>"

    text = re.sub(r"(^\d+\. .+$\n?)+", _ol, text, flags=re.MULTILINE)

    # Paragraphs / line breaks
    text = text.replace("\n\n", "<br><br>")
    text = text.replace("\n", "<br>")

    # Clean extra <br> around block elements
    text = re.sub(r"(</(?:pre|ul|ol|table|h[2-4])>)(?:<br>)+", r"\1", text)
    text = re.sub(r"(?:<br>)+(<(?:pre|ul|ol|table|h[2-4])[> ])", r"\1", text)

    # Restore stashed code blocks and tables
    for idx, block in enumerate(blocks):
        text = text.replace(f"\x00CB{idx}\x00", block)

    return text
