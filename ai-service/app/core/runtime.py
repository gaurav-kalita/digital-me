# ai-service2/app/core/runtime.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.core.config import settings


@dataclass(frozen=True)
class RuntimeCheck:
    name: str
    status: str
    critical: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def is_passing(self) -> bool:
        return self.status == "pass"


@dataclass(frozen=True)
class RuntimeStatus:
    service: str
    version: str
    status: str
    ready: bool
    checked_at: datetime
    checks: List[RuntimeCheck] = field(default_factory=list)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "version": self.version,
            "status": self.status,
            "ready": self.ready,
            "checked_at": self.checked_at,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "critical": check.critical,
                    "details": check.details,
                }
                for check in self.checks
            ],
        }


def build_runtime_status(
    data_dir: Optional[str] = None,
    index_artifact_path: Optional[str] = None,
    faiss_index_path: Optional[str] = None,
    faiss_metadata_path: Optional[str] = None,
) -> RuntimeStatus:
    selected_data_dir = Path(data_dir or settings.DATA_DIR)
    selected_index_artifact_path = Path(index_artifact_path or settings.INDEX_ARTIFACT_PATH)
    selected_faiss_index_path = Path(faiss_index_path or settings.FAISS_INDEX_PATH)
    selected_faiss_metadata_path = Path(faiss_metadata_path or settings.FAISS_METADATA_PATH)

    source_files = _list_source_files(selected_data_dir)
    index_files = [
        selected_index_artifact_path,
        selected_faiss_index_path,
        selected_faiss_metadata_path,
    ]
    index_files_present = [path for path in index_files if path.exists()]
    index_artifact_mtime = _latest_mtime(index_files_present)
    source_mtime = _latest_mtime(source_files)

    checks = [
        RuntimeCheck(
            name="data_dir",
            status="pass" if selected_data_dir.exists() else "fail",
            critical=True,
            details={
                "path": str(selected_data_dir),
                "exists": selected_data_dir.exists(),
                "source_file_count": len(source_files),
            },
        ),
        RuntimeCheck(
            name="index_artifacts",
            status="pass" if len(index_files_present) == len(index_files) else "fail",
            critical=True,
            details={
                "artifact_path": str(selected_index_artifact_path),
                "faiss_index_path": str(selected_faiss_index_path),
                "faiss_metadata_path": str(selected_faiss_metadata_path),
                "present_count": len(index_files_present),
                "expected_count": len(index_files),
            },
        ),
        RuntimeCheck(
            name="index_freshness",
            status="pass" if _is_index_fresh(source_mtime, index_artifact_mtime) else "warn",
            critical=False,
            details={
                "latest_source_mtime": source_mtime.isoformat() if source_mtime else None,
                "latest_index_mtime": index_artifact_mtime.isoformat() if index_artifact_mtime else None,
            },
        ),
    ]

    cache_check = _build_cache_check()
    checks.append(cache_check)

    ready = all(check.is_passing() for check in checks if check.critical)
    status = "healthy" if all(check.is_passing() for check in checks) else "degraded"

    return RuntimeStatus(
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        status=status,
        ready=ready,
        checked_at=datetime.now(timezone.utc),
        checks=checks,
    )


def _build_cache_check() -> RuntimeCheck:
    from app.bootstrap.composition import build_cache_store

    cache_store = build_cache_store()
    diagnostics = getattr(cache_store, "diagnostics", None)
    if diagnostics is None:
        return RuntimeCheck(
            name="cache",
            status="pass",
            critical=False,
            details={"enabled": settings.cache.enabled, "backend": type(cache_store).__name__},
        )

    details = diagnostics()
    status = "pass" if details.get("available", True) else "warn"
    return RuntimeCheck(name="cache", status=status, critical=False, details=details)


def _list_source_files(data_dir: Path) -> List[Path]:
    if not data_dir.exists():
        return []

    files: List[Path] = []
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue
        if ".index" in path.parts:
            continue
        if path.name.startswith("."):
            continue
        files.append(path)
    return files


def _latest_mtime(paths: Iterable[Path]) -> Optional[datetime]:
    timestamps = [datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) for path in paths if path.exists()]
    if not timestamps:
        return None
    return max(timestamps)


def _is_index_fresh(source_mtime: Optional[datetime], index_mtime: Optional[datetime]) -> bool:
    if source_mtime is None:
        return False
    if index_mtime is None:
        return False
    return index_mtime >= source_mtime
