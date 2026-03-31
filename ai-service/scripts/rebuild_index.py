"""Rebuild the offline RAG index artifacts from source data."""

from app.repositories.vector_repository import VectorRepository


def main() -> None:
    repository = VectorRepository()
    chunks = repository.rebuild()
    print("Indexed %s chunks" % len(chunks))


if __name__ == "__main__":
    main()
