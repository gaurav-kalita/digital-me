"""Rebuild the offline RAG index artifacts from source data."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.bootstrap.composition import build_knowledge_index_use_case


def main() -> None:
    use_case = build_knowledge_index_use_case()
    chunks = use_case.execute()
    print("Indexed %s chunks" % len(chunks))


if __name__ == "__main__":
    main()
