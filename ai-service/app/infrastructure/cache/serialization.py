"""Serialization helpers for cache payloads."""

import json
from dataclasses import asdict
from typing import Iterable, List

from app.data_layer.models import RetrievalResult


def serialize_retrieval_results(results: Iterable[RetrievalResult]) -> str:
    return json.dumps([asdict(result) for result in results], ensure_ascii=True)


def deserialize_retrieval_results(payload: str) -> List[RetrievalResult]:
    items = json.loads(payload)
    return [RetrievalResult(**item) for item in items]


def serialize_mapping(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True)


def deserialize_mapping(payload: str) -> dict:
    return json.loads(payload)
