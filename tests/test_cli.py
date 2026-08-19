from pathlib import Path

from typer.testing import CliRunner

from quackvideo.cli import app
from quackvideo.providers.transcription import FakeTranscriptionProvider

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.2.0" in result.stdout


def test_cli_doctor_json() -> None:
    result = runner.invoke(app, ["--json", "doctor"])
    assert result.exit_code in {0, 2}
    assert "ffmpeg" in result.stdout


def test_project_init(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    result = runner.invoke(app, ["project", "init", "--name", "studio", "--workspace", str(tmp_path / "ws")])
    assert result.exit_code == 0
    assert (tmp_path / "quackvideo.toml").exists()


def test_fake_transcript_is_deterministic() -> None:
    provider = FakeTranscriptionProvider()
    first = provider.transcribe("x.flac", 40, "en", "hash")
    second = provider.transcribe("x.flac", 40, "en", "hash")
    assert first.full_text == second.full_text
    assert first.segments
    assert first.segments[-1].end <= 40.1
