# ai-service2/app/api/endpoints/health.py

from fastapi import APIRouter, Response, status

from app.core.runtime import build_runtime_status
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def health(response: Response):
    runtime_status = build_runtime_status()
    response.status_code = status.HTTP_200_OK if runtime_status.ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return runtime_status.to_payload()

