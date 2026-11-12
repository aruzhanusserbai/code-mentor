from pathlib import Path

import pytest

import agent.main as main_module


def test_missing_model_is_reported_as_annotation_without_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(main_module, "PLATFORM_ROOT", tmp_path)  # no local .env
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-must-not-appear")
    monkeypatch.delenv("CODEMENTOR_MODEL", raising=False)

    code = main_module.main(
        ["--ticket", "1", "--repo", str(tmp_path), "--test-output", "x.txt", "--out", str(tmp_path / "c.md")]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "::error title=CodeMentor agent::missing environment variables: CODEMENTOR_MODEL" in captured.out
    assert "sk-test-must-not-appear" not in captured.out + captured.err
    assert not (tmp_path / "c.md").exists()
