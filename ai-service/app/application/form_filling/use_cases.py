# ai-service2/app/application/form_filling/use_cases.py

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.application.form_filling.dto import (
    FormFillCommand,
    FormFillResult,
    FormFieldDescriptor,
    FormFieldPlan,
)
from app.core.exceptions import AIServiceError
from app.core.logger import logger
from app.core.ports import ContextBuilder, LLMProvider, QueryProcessor, Reranker, RetrievalGateway
from app.data_layer.models import RetrievalResult

CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class DefaultPlanFormFillUseCase:
    """Produces a structured fill plan for a scanned page form."""

    def __init__(
        self,
        query_processor: QueryProcessor,
        retriever: RetrievalGateway,
        reranker: Reranker,
        context_builder: ContextBuilder,
        provider: LLMProvider,
        max_concurrent_plans: int = 4,
    ):
        self.query_processor = query_processor
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder
        self.provider = provider
        self.max_concurrent_plans = max(1, max_concurrent_plans)

    async def execute(self, command: FormFillCommand) -> FormFillResult:
        try:
            started_at = time.perf_counter()
            query = self._build_query(command)
            processed_query = self.query_processor.process(query)
            queries = self._expand_queries(processed_query)
            candidates = await self.retriever.retrieve(queries)
            ranked = self.rerank(command=command, query=query, candidates=candidates)
            _, selected = self.context_builder.build(query=query, candidates=ranked)
            prompt = self._build_prompt(command=command, selected_context=selected)
            raw_response = await self.provider.generate(prompt)
            plan_payload = self._parse_response(raw_response)
            result = self._to_result(command=command, payload=plan_payload, metadata={
                "query": query,
                "candidates": len(candidates),
                "selected": len(selected),
                "total_ms": round((time.perf_counter() - started_at) * 1000, 2),
            })
            logger.info(
                "form fill plan generated",
                extra={
                    "site": command.site,
                    "page_url": command.page_url,
                    "fields": len(command.fields),
                    "actions": len(result.actions),
                },
            )
            return result
        except AIServiceError:
            raise
        except Exception as exc:
            logger.bind(error=str(exc), exception_type=type(exc).__name__).opt(exception=exc).error(
                "Form fill planning failed"
            )
            raise AIServiceError("Failed to build form fill plan") from exc

    def rerank(self, command: FormFillCommand, query: str, candidates: Sequence[RetrievalResult]) -> List[RetrievalResult]:
        return self.reranker.rank(query=query, candidates=candidates)

    def _build_query(self, command: FormFillCommand) -> str:
        field_summaries = [
            "%s|%s|%s|%s"
            % (
                field.field_id,
                field.label,
                field.field_type,
                field.placeholder or field.name or field.autocomplete,
            )
            for field in command.fields
        ]
        return (
            "Fill the current form for %s on %s. "
            "Fields: %s."
        ) % (
            command.site,
            command.page_title or command.page_url,
            " ; ".join(field_summaries),
        )

    def _expand_queries(self, processed_query: Dict[str, Any]) -> List[str]:
        queries: List[str] = []
        seen = set()

        for value in [
            processed_query.get("rewritten_query"),
            processed_query.get("normalized_query"),
            processed_query.get("original_query"),
        ]:
            if value and value not in seen:
                queries.append(value)
                seen.add(value)

        for value in processed_query.get("queries", []):
            if value and value not in seen:
                queries.append(value)
                seen.add(value)

        return queries or [processed_query.get("original_query", "")]

    def _build_prompt(self, command: FormFillCommand, selected_context: Sequence[RetrievalResult]) -> str:
        context_lines = []
        for item in selected_context:
            context_lines.append(
                "SOURCE: %s\nLABEL: %s\nTEXT: %s"
                % (item.title, item.to_source_label(), item.text)
            )

        field_payload = [
            {
                "field_id": field.field_id,
                "label": field.label,
                "field_type": field.field_type,
                "tag_name": field.tag_name,
                "name": field.name,
                "placeholder": field.placeholder,
                "autocomplete": field.autocomplete,
                "aria_label": field.aria_label,
                "current_value": field.current_value,
                "required": field.required,
                "visible": field.visible,
                "disabled": field.disabled,
                "options": field.options,
                "page_hints": field.page_hints,
            }
            for field in command.fields
        ]

        return (
            "SYSTEM:\n"
            "You are a browser form filling assistant for a single user profile.\n"
            "Use only the provided context. Never invent data.\n"
            "Return strict JSON only with this schema:\n"
            "{\n"
            '  "site": string,\n'
            '  "page_url": string,\n'
            '  "actions": [\n'
            "    {\n"
            '      "field_id": string,\n'
            '      "action": "fill" | "skip",\n'
            '      "value": string,\n'
            '      "confidence": number,\n'
            '      "risk": "low" | "medium" | "high",\n'
            '      "reason": string,\n'
            '      "source_labels": [string],\n'
            '      "matched_field": string\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "If the value is uncertain, use action=skip.\n"
            "Do not add commentary or markdown.\n\n"
            "PAGE:\n%s\n\n"
            "FIELDS:\n%s\n\n"
            "CONTEXT:\n%s\n"
        ) % (
            json.dumps(
                {
                    "site": command.site,
                    "page_url": command.page_url,
                    "page_title": command.page_title,
                },
                indent=2,
            ),
            json.dumps(field_payload, indent=2),
            "\n\n".join(context_lines) or "No relevant context retrieved.",
        )

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        payload = raw_response.strip()
        payload = CODE_FENCE_PATTERN.sub("", payload).strip()
        parsed = json.loads(payload)
        if isinstance(parsed, list):
            return {"actions": parsed}
        if not isinstance(parsed, dict):
            raise ValueError("Form fill response must be a JSON object")
        return parsed

    def _to_result(self, command: FormFillCommand, payload: Dict[str, Any], metadata: Dict[str, Any]) -> FormFillResult:
        actions_payload = payload.get("actions", [])
        action_map = {item.field_id: item for item in command.fields}
        actions: List[FormFieldPlan] = []
        skipped: List[str] = []

        for item in actions_payload:
            field_id = str(item.get("field_id", "")).strip()
            if not field_id:
                continue

            action = str(item.get("action", "fill")).strip().lower()
            value = str(item.get("value", "") or "")
            confidence = float(item.get("confidence", 0.0) or 0.0)
            risk = str(item.get("risk", "low") or "low")
            reason = str(item.get("reason", "") or "")
            source_labels = [str(value) for value in item.get("source_labels", []) if str(value).strip()]
            matched_field = str(item.get("matched_field", "") or "")

            actions.append(
                FormFieldPlan(
                    field_id=field_id,
                    value=value,
                    action=action,
                    confidence=confidence,
                    risk=risk,
                    reason=reason,
                    source_labels=source_labels,
                    matched_field=matched_field,
                )
            )
            if action != "fill":
                skipped.append(field_id)

        known_field_ids = {field.field_id for field in command.fields}
        for field_id in known_field_ids:
            if field_id not in {item.field_id for item in actions}:
                skipped.append(field_id)

        return FormFillResult(
            site=payload.get("site", command.site),
            page_url=payload.get("page_url", command.page_url),
            page_title=command.page_title,
            actions=actions,
            skipped=sorted(set(skipped)),
            metadata=metadata,
        )
