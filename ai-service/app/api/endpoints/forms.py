# ai-service2/app/api/endpoints/forms.py

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.form_filling.dto import FormFillCommand, FormFieldDescriptor
from app.application.form_filling.use_cases import DefaultPlanFormFillUseCase
from app.bootstrap.composition import build_form_fill_use_case
from app.schemas.form_fill import FormFillPlanRequest, FormFillPlanResponse

router = APIRouter()


def _to_command(request: FormFillPlanRequest) -> FormFillCommand:
    return FormFillCommand(
        site=request.site,
        page_url=request.page_url,
        page_title=request.page_title,
        fields=[
            FormFieldDescriptor(
                field_id=field.field_id,
                label=field.label,
                field_type=field.field_type,
                tag_name=field.tag_name,
                name=field.name,
                placeholder=field.placeholder,
                autocomplete=field.autocomplete,
                aria_label=field.aria_label,
                current_value=field.current_value,
                required=field.required,
                visible=field.visible,
                disabled=field.disabled,
                options=field.options,
                page_hints=field.page_hints,
            )
            for field in request.fields
        ],
    )


@router.post("/plan", response_model=FormFillPlanResponse)
async def plan_form_fill(
    request: FormFillPlanRequest,
    planner: DefaultPlanFormFillUseCase = Depends(build_form_fill_use_case),
):
    if not request.fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No form fields were provided")
    result = await planner.execute(_to_command(request))
    return {
        "site": result.site,
        "page_url": result.page_url,
        "page_title": result.page_title,
        "actions": [
            {
                "field_id": action.field_id,
                "action": action.action,
                "value": action.value,
                "confidence": action.confidence,
                "risk": action.risk,
                "reason": action.reason,
                "source_labels": action.source_labels,
                "matched_field": action.matched_field,
            }
            for action in result.actions
        ],
        "skipped": result.skipped,
        "metadata": result.metadata,
    }
