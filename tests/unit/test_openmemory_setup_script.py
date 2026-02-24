import shutil
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENMEMORY_DIR = REPO_ROOT / "extras" / "openmemory-mcp"


def _prepare_tmp_setup(tmp_path: Path) -> Path:
    setup_src = OPENMEMORY_DIR / "setup.sh"
    template_src = OPENMEMORY_DIR / ".env.template"

    setup_dst = tmp_path / "setup.sh"
    template_dst = tmp_path / ".env.template"

    shutil.copy2(setup_src, setup_dst)
    shutil.copy2(template_src, template_dst)

    setup_dst.chmod(setup_dst.stat().st_mode | stat.S_IXUSR)
    return setup_dst


def _read_env_map(env_path: Path) -> dict[str, str]:
    data = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def test_setup_openai_embeddings_mode_writes_expected_env(tmp_path):
    setup_script = _prepare_tmp_setup(tmp_path)

    subprocess.run(
        [
            "bash",
            str(setup_script),
            "--embeddings-provider",
            "openai",
            "--openai-api-key",
            "sk-test-openai",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    env_map = _read_env_map(tmp_path / ".env")
    assert env_map["OPENMEMORY_EMBEDDINGS_PROVIDER"] == "openai"
    assert env_map["OPENAI_API_KEY"] == "sk-test-openai"
    assert env_map["OPENAI_BASE_URL"] == ""
    assert env_map["OPENAI_EMBEDDING_MODEL"] == ""
    assert env_map["OPENAI_EMBEDDING_DIMENSIONS"] == ""


def test_setup_local_embeddings_mode_writes_expected_env(tmp_path):
    setup_script = _prepare_tmp_setup(tmp_path)

    subprocess.run(
        [
            "bash",
            str(setup_script),
            "--embeddings-provider",
            "local",
            "--embeddings-base-url",
            "http://host.docker.internal:11434/v1",
            "--embeddings-model",
            "nomic-embed-text",
            "--embeddings-api-key",
            "local-key",
            "--embeddings-dimensions",
            "768",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    env_map = _read_env_map(tmp_path / ".env")
    assert env_map["OPENMEMORY_EMBEDDINGS_PROVIDER"] == "local"
    assert env_map["OPENAI_API_KEY"] == "local-key"
    assert env_map["OPENAI_BASE_URL"] == "http://host.docker.internal:11434/v1"
    assert env_map["OPENAI_EMBEDDING_MODEL"] == "nomic-embed-text"
    assert env_map["OPENAI_EMBEDDING_DIMENSIONS"] == "768"
    assert (
        env_map["OPENMEMORY_EMBEDDINGS_BASE_URL"]
        == "http://host.docker.internal:11434/v1"
    )
    assert env_map["OPENMEMORY_EMBEDDINGS_MODEL"] == "nomic-embed-text"
    assert env_map["OPENMEMORY_EMBEDDINGS_API_KEY"] == "local-key"
    assert env_map["OPENMEMORY_EMBEDDINGS_DIMENSIONS"] == "768"


def test_setup_rejects_invalid_embeddings_provider(tmp_path):
    setup_script = _prepare_tmp_setup(tmp_path)

    result = subprocess.run(
        ["bash", str(setup_script), "--embeddings-provider", "invalid-provider"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--embeddings-provider must be 'openai' or 'local'" in result.stderr
