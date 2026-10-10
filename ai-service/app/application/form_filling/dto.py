# ai-service2/app/application/form_filling/dto.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FormFieldDescriptor:
    field_id: str
    label: str
    field_type: str
    tag_name: str
    name: str = ""
    placeholder: str = ""
    autocomplete: str = ""
    aria_label: str = ""
    current_value: str = ""
    required: bool = False
    visible: bool = True
    disabled: bool = False
    options: List[str] = field(default_factory=list)
    page_hints: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FormFillCommand:
    site: str
    page_url: str
    page_title: str
    fields: List[FormFieldDescriptor]
    user_id: str = "anonymous"


@dataclass(frozen=True)
class FormFieldPlan:
    field_id: str
    value: str
    action: str = "fill"
    confidence: float = 0.0
    risk: str = "low"
    reason: str = ""
    source_labels: List[str] = field(default_factory=list)
    matched_field: str = ""


@dataclass(frozen=True)
class FormFillResult:
    site: str
    page_url: str
    page_title: str
    actions: List[FormFieldPlan] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

