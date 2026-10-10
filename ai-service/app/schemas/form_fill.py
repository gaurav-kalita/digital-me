# ai-service2/app/schemas/form_fill.py

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class FormFieldInput(BaseModel):
    field_id: str = Field(..., min_length=1)
    label: str = Field(default="")
    field_type: str = Field(default="")
    tag_name: str = Field(default="")
    name: str = Field(default="")
    placeholder: str = Field(default="")
    autocomplete: str = Field(default="")
    aria_label: str = Field(default="")
    current_value: str = Field(default="")
    required: bool = False
    visible: bool = True
    disabled: bool = False
    options: List[str] = Field(default_factory=list)
    page_hints: Dict[str, Any] = Field(default_factory=dict)


class FormFillPlanRequest(BaseModel):
    site: str = Field(default="unknown-site")
    page_url: str = Field(default="")
    page_title: str = Field(default="")
    fields: List[FormFieldInput] = Field(default_factory=list)


class FormFillAction(BaseModel):
    field_id: str
    action: Literal["fill", "skip"] = "fill"
    value: str = ""
    confidence: float = 0.0
    risk: Literal["low", "medium", "high"] = "low"
    reason: str = ""
    source_labels: List[str] = Field(default_factory=list)
    matched_field: str = ""


class FormFillPlanResponse(BaseModel):
    site: str
    page_url: str
    page_title: str
    actions: List[FormFillAction] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

