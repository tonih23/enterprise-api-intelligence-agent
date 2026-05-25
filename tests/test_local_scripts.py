"""Contract tests for safe local developer convenience scripts."""

from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[1]
SCRIPT_DIR = PROJECT_ROOT / "local_scripts"
SCRIPT_NAMES = ("run_backend.sh", "run_ui.sh", "run_evals.sh")


def script_text(name: str) -> str:
    return (SCRIPT_DIR / name).read_text(encoding="utf-8")


def test_local_env_is_ignored_while_placeholder_template_remains_versionable() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    template = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert ".env\n" in gitignore
    assert "!.env.example" in gitignore
    assert '# GOOGLE_API_KEY=""' in template
    assert '# LANGSMITH_API_KEY=""' in template


@pytest.mark.parametrize("script_name", SCRIPT_NAMES)
def test_local_script_is_executable_valid_shell_and_contains_no_key(
    script_name: str,
) -> None:
    path = SCRIPT_DIR / script_name
    content = script_text(script_name)

    assert path.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(path)], check=True)
    assert "GOOGLE_API_KEY" not in content
    assert "LANGSMITH_API_KEY" not in content


@pytest.mark.parametrize("script_name", SCRIPT_NAMES)
def test_local_script_explains_how_to_create_missing_env(
    tmp_path: Path, script_name: str
) -> None:
    local_scripts = tmp_path / "local_scripts"
    local_scripts.mkdir()
    copied_script = local_scripts / script_name
    shutil.copy2(SCRIPT_DIR / script_name, copied_script)

    result = subprocess.run(
        ["bash", str(copied_script)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "Missing .env" in result.stderr
    assert "cp .env.example .env" in result.stderr


def test_backend_script_starts_dependencies_ingests_and_launches_api() -> None:
    content = script_text("run_backend.sh")

    assert (
        'docker compose --env-file ".env" up -d --wait opensearch postgres phoenix'
        in content
    )
    assert "uv run python scripts/ingest_docs.py" in content
    assert "exec uv run uvicorn app.main:app --reload" in content


def test_ui_and_eval_scripts_launch_expected_local_commands() -> None:
    assert "exec uv run streamlit run demo/streamlit_app.py" in script_text("run_ui.sh")
    eval_content = script_text("run_evals.sh")
    assert "uv run pytest" in eval_content
    assert "uv run python -m app.evals.run_evals" in eval_content
