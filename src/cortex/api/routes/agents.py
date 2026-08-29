from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def list_agents(request: Request) -> list[dict]:
    return [a.model_dump(exclude={"instructions"}) for a in request.app.state.registry.agents]
