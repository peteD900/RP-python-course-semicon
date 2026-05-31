"""Report renderers: Open/Closed Principle in action.

Introduced in Day 4. Adding a new report format means adding a new subclass —
nothing in this file or in the calling code needs to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

__all__ = ["ReportRenderer", "HTMLRenderer", "MarkdownRenderer"]


class ReportRenderer(ABC):
    """Abstract base for all report formats.

    Each subclass implements ``render(sections)``; ``save()`` is provided
    for free and works for every format — the Template Method pattern.

    To add a new format, subclass here. Never edit existing subclasses.
    That's the Open/Closed Principle: open for extension, closed for modification.
    """

    @abstractmethod
    def render(self, sections: dict[str, str]) -> str:
        """Turn a dict of {section_title: content} into a formatted string."""
        ...

    def save(self, sections: dict[str, str], path: str | Path) -> None:
        """Render and write to *path*. Free for every subclass."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.render(sections), encoding="utf-8")


class HTMLRenderer(ReportRenderer):
    """Minimal HTML report — a hook for Quarto/Jinja to replace later."""

    def render(self, sections: dict[str, str]) -> str:
        parts = ["<html><body>"]
        for title, content in sections.items():
            parts.append(f"  <h2>{title}</h2>\n  <pre>{content}</pre>")
        parts.append("</body></html>")
        return "\n".join(parts)


class MarkdownRenderer(ReportRenderer):
    def render(self, sections: dict[str, str]) -> str:
        parts = []
        for title, content in sections.items():
            parts.append(f"## {title}\n\n{content}\n")
        return "\n".join(parts)
