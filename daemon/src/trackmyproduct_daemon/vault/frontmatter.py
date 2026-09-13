"""Read/write Markdown notes with YAML frontmatter, per docs/data-model.md.

The note body (everything after the closing ``---``) is the user's free-form
text and is preserved byte-for-byte on write; the daemon only ever rewrites
the frontmatter block.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

FRONTMATTER_DELIM = "---"


@dataclass
class Note:
    frontmatter: dict
    body: str


def parse_note(text: str) -> Note:
    """Split a note's raw text into frontmatter dict + body string.

    Tolerates a missing frontmatter block (returns an empty dict + the full
    text as body) so a hand-created stray file doesn't crash the daemon.
    """
    if not text.startswith(FRONTMATTER_DELIM):
        return Note(frontmatter={}, body=text)

    # text looks like: "---\n<yaml>\n---\n<body>"
    rest = text[len(FRONTMATTER_DELIM):]
    parts = rest.split(f"\n{FRONTMATTER_DELIM}", 1)
    if len(parts) != 2:
        return Note(frontmatter={}, body=text)

    yaml_block, body = parts
    data = yaml.safe_load(yaml_block) or {}
    if not isinstance(data, dict):
        data = {}
    # Drop the leading newline left over from the delimiter split, keep the rest.
    body = body[1:] if body.startswith("\n") else body
    return Note(frontmatter=data, body=body)


def render_note(frontmatter: dict, body: str) -> str:
    yaml_block = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    return f"{FRONTMATTER_DELIM}\n{yaml_block}{FRONTMATTER_DELIM}\n{body}"


def read_note(path: Path) -> Note:
    return parse_note(path.read_text(encoding="utf-8"))


def write_note(path: Path, frontmatter: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_note(frontmatter, body), encoding="utf-8")
