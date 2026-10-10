# ai-service2/app/application/form_filling/ports.py

from typing import Protocol

from app.application.form_filling.dto import FormFillCommand, FormFillResult


class PlanFormFillUseCase(Protocol):
    async def execute(self, command: FormFillCommand) -> FormFillResult:
        ...

