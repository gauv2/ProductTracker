from pathlib import Path

from trackmyproduct_daemon.vault.frontmatter import parse_note, read_note, render_note, write_note


def test_round_trip_preserves_frontmatter_and_body(tmp_path: Path):
    frontmatter = {
        "tmp_id": "a1b2c3",
        "tmp_type": "product",
        "name": "NVIDIA DGX Spark",
        "saved_searches": [
            {"id": "ss-1", "platforms": ["marktplaats", "ebay"], "enabled": True}
        ],
        "listings": [],
    }
    body = "\nSome personal notes about this product.\n- bullet\n"

    path = tmp_path / "note.md"
    write_note(path, frontmatter, body)

    note = read_note(path)
    assert note.frontmatter == frontmatter
    assert note.body == body


def test_parse_note_handles_missing_frontmatter():
    note = parse_note("just some text, no frontmatter here")
    assert note.frontmatter == {}
    assert note.body == "just some text, no frontmatter here"


def test_render_then_parse_is_idempotent():
    frontmatter = {"a": 1, "b": [1, 2, 3], "c": None}
    body = "body text"
    rendered = render_note(frontmatter, body)
    parsed = parse_note(rendered)
    assert parsed.frontmatter == frontmatter
    assert parsed.body == body


def test_write_note_creates_parent_directories(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "note.md"
    write_note(path, {"x": 1}, "body")
    assert path.exists()
    assert read_note(path).frontmatter == {"x": 1}
