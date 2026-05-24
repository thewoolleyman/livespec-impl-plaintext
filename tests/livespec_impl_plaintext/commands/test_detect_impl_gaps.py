"""Tests for the detect-impl-gaps thin-transport command."""

import json
from pathlib import Path

import pytest
from livespec_impl_plaintext.commands.detect_impl_gaps import (
    detect_rules,
    main,
)


def _write_spec(*, root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    history = root / "history" / "v001"
    history.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (root / name).write_text(content)


def test_main_no_rules_human_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(root=spec, files={"spec.md": "# Heading\n\nNo rules here.\n"})
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "(no rules detected)" in captured.out


def test_main_detects_must_and_should_rules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={
            "spec.md": (
                "# Top\n\n"
                "## Section A\n\n"
                "Every reader MUST validate the input.\n"
                "Implementations SHOULD prefer the typed API.\n"
                "Callers MUST NOT pass null.\n"
                "Plugins SHOULD NOT shell out.\n"
                "\n"
                "## Section B\n\n"
                "Just a normal paragraph with must in lowercase — no rule.\n"
            ),
        },
    )
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "MUST validate" in captured.out
    assert "SHOULD prefer" in captured.out
    assert "MUST NOT pass" in captured.out
    assert "SHOULD NOT shell out" in captured.out
    # Lowercase 'must' MUST NOT match.
    assert "no rule" not in captured.out


def test_main_excludes_code_fences(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={
            "spec.md": (
                "# Top\n\n"
                "Outside the fence: implementations MUST honor this.\n"
                "\n"
                "```python\n"
                "# inside fence: this MUST be skipped\n"
                "def f(): pass\n"
                "```\n"
                "\n"
                "After the fence: callers SHOULD retry.\n"
            ),
        },
    )
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "MUST honor" in captured.out
    assert "SHOULD retry" in captured.out
    assert "MUST be skipped" not in captured.out


def test_main_emits_json_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={"spec.md": "# T\n\nEverything MUST be deterministic.\n"},
    )
    rc = main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert "gap_ids" in payload
    assert len(payload["gap_ids"]) == 1
    assert payload["gap_ids"][0].startswith("gap-")


def test_main_excludes_proposed_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={"spec.md": "# T\n\nLive rules MUST land here.\n"},
    )
    proposed = spec / "proposed_changes"
    proposed.mkdir()
    (proposed / "draft.md").write_text("# Draft\n\nThis pending rule MUST not surface.\n")
    rc = main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    # Only the live spec.md rule surfaces; the proposed_changes draft does not.
    assert len(payload["gap_ids"]) == 1


def test_main_uses_explicit_spec_target_and_project_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "elsewhere"
    spec = project / "MyCustomSpec"
    _write_spec(root=spec, files={"spec.md": "# T\n\nReaders MUST cope.\n"})
    rc = main(["--project-root", str(project), "--spec-target", str(spec), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert len(payload["gap_ids"]) == 1


def test_main_project_root_with_default_spec_target(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "elsewhere"
    spec = project / "SPECIFICATION"
    _write_spec(root=spec, files={"spec.md": "# T\n\nReaders MUST cope.\n"})
    rc = main(["--project-root", str(project), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert len(payload["gap_ids"]) == 1


def test_main_skips_non_markdown_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={
            "spec.md": "# T\n\nMarkdown rule MUST surface.\n",
            "schema.json": '{"note": "JSON files MUST not be scanned"}\n',
        },
    )
    rc = main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert len(payload["gap_ids"]) == 1


def test_main_skips_blank_lines_with_keyword(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A line that's only whitespace MUST NOT count even if the regex
    # would otherwise match (defensive — the regex needs a real word
    # boundary).
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={
            "spec.md": (
                "# Top\n"
                "\n"
                "MUST\n"  # standalone keyword on its own line — still a rule
                "\n"
                "Real rule: callers MUST do X.\n"
            ),
        },
    )
    rc = main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    # Two non-empty lines matched: "MUST" alone and "callers MUST do X."
    assert len(payload["gap_ids"]) == 2


def test_main_detects_rule_at_top_of_file_without_heading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={"spec.md": "Readers MUST handle the no-heading case.\n# Then Heading\n"},
    )
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "(top)" in captured.out


def test_main_heading_stack_handles_level_jumps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Skip from H1 directly to H3 (no H2). Stack should pad an empty H2.
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={
            "spec.md": (
                "# H1\n"
                "\n"
                "### H3 (jumped)\n"
                "\n"
                "Rule MUST appear under jumped heading path.\n"
            ),
        },
    )
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "H1 >  > H3 (jumped)" in captured.out


def test_detect_rules_deterministic_across_calls(tmp_path: Path) -> None:
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={"spec.md": "# Heading\n\nReaders MUST cope.\nCallers SHOULD retry.\n"},
    )
    first = detect_rules(spec_root=spec)
    second = detect_rules(spec_root=spec)
    assert [r.gap_id for r in first] == [r.gap_id for r in second]


def test_detect_rules_returns_sorted_by_file_heading_text(tmp_path: Path) -> None:
    spec = tmp_path / "SPECIFICATION"
    _write_spec(
        root=spec,
        files={
            "z_last.md": "# Z\n\nFile Z MUST appear after.\n",
            "a_first.md": "# A\n\nFile A MUST appear first.\n",
        },
    )
    rules = detect_rules(spec_root=spec)
    spec_files = [r.spec_file for r in rules]
    assert spec_files == sorted(spec_files)
