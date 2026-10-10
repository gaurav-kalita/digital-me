import shutil
import uuid
from pathlib import Path

from app.core.runtime import build_runtime_status


def _workspace_temp_dir() -> Path:
    root = Path.cwd() / "test_scratch"
    root.mkdir(exist_ok=True)
    temp_dir = root / ("runtime-tests-" + uuid.uuid4().hex)
    temp_dir.mkdir()
    return temp_dir


def test_runtime_status_is_ready_when_artifacts_exist_and_are_fresh():
    temp_dir = _workspace_temp_dir()
    try:
        data_dir = temp_dir / "data"
        index_dir = temp_dir / ".index"
        data_dir.mkdir()
        index_dir.mkdir()

        (data_dir / "profile.txt").write_text("Fresh data for a ready service.", encoding="utf-8")
        (index_dir / "chunks.json").write_text("[]", encoding="utf-8")
        (index_dir / "chunks.faiss").write_bytes(b"faiss")
        (index_dir / "chunks.metadata.json").write_text("[]", encoding="utf-8")

        runtime = build_runtime_status(
            data_dir=str(data_dir),
            index_artifact_path=str(index_dir / "chunks.json"),
            faiss_index_path=str(index_dir / "chunks.faiss"),
            faiss_metadata_path=str(index_dir / "chunks.metadata.json"),
        )

        assert runtime.ready is True
        assert runtime.status in {"healthy", "degraded"}
        assert any(check.name == "cache" for check in runtime.checks)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_runtime_status_is_not_ready_when_index_artifacts_are_missing():
    temp_dir = _workspace_temp_dir()
    try:
        data_dir = temp_dir / "data"
        data_dir.mkdir()
        (data_dir / "profile.txt").write_text("Missing index artifacts.", encoding="utf-8")

        runtime = build_runtime_status(
            data_dir=str(data_dir),
            index_artifact_path=str(temp_dir / ".index" / "chunks.json"),
            faiss_index_path=str(temp_dir / ".index" / "chunks.faiss"),
            faiss_metadata_path=str(temp_dir / ".index" / "chunks.metadata.json"),
        )

        assert runtime.ready is False
        assert runtime.status == "degraded"
        assert any(check.name == "index_artifacts" and check.status == "fail" for check in runtime.checks)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
