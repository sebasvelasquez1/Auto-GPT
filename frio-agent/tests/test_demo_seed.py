"""`frio demo-seed` — one command that produces a real, viewable business verdict."""

from __future__ import annotations

from typer.testing import CliRunner

from frio.cli import app

runner = CliRunner()


def test_demo_seed_produces_a_scale_and_a_cancel_verdict(tmp_path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path/'seed.db'}"
    monkeypatch.setenv("FRIO_DATABASE_URL", url)

    seed = runner.invoke(app, ["demo-seed"])
    assert seed.exit_code == 0, seed.output

    summary = runner.invoke(app, ["analyzer", "summary"])
    assert summary.exit_code == 0, summary.output
    assert "SCALE" in summary.output
    assert "CANCEL" in summary.output
