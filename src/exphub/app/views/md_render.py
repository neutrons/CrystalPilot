"""Lightweight Markdown to HTML converter for chat bubbles.

Handles common markdown features without external dependencies:
fenced code blocks, inline code, bold, italic, headers, lists.
"""

from __future__ import annotations

import re
from html import escape


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
    text = re.sub(r"(</(?:pre|ul|ol|h[2-4])>)(?:<br>)+", r"\1", text)
    text = re.sub(r"(?:<br>)+(<(?:pre|ul|ol|h[2-4])[> ])", r"\1", text)

    # Restore stashed code blocks
    for idx, block in enumerate(blocks):
        text = text.replace(f"\x00CB{idx}\x00", block)

    return text
