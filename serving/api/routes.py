from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from inference.config import MODEL_NAME, QUEUE_ENABLED
from serving.models.schemas import ChatRequest, ChatResponse
from serving.orchestration.agent_loop import (
    run_agent_from_messages_direct,
    run_agent_from_openai_payload_direct,
    stream_agent_from_openai_payload_direct,
)
from serving.queue.kafka_queue import submit_agent_job_and_stream, submit_agent_job_and_wait
from serving.tools.registry import list_tools


router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "serving-backend"}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/tools")
async def tools() -> dict[str, Any]:
    return {"tools": await list_tools(refresh=True)}


@router.get("/v1/models")
async def openai_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": 0,
                "owned_by": "backend",
            }
        ],
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    messages = [message.model_dump(exclude_none=True) for message in request.messages]

    if QUEUE_ENABLED:
        payload = {
            "model": request.model or MODEL_NAME,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        raw = await submit_agent_job_and_wait(payload=payload, endpoint="/chat")
        choice = raw.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        return ChatResponse(
            content=content,
            tool_rounds=raw.get("backend", {}).get("tool_rounds", 0),
            raw=raw,
        )

    result = await run_agent_from_messages_direct(
        incoming_messages=messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        conversation_id=request.conversation_id,
        endpoint="/chat",
    )

    return ChatResponse(
        content=result.content,
        tool_rounds=result.tool_rounds,
        raw={
            "conversation_id": result.conversation_id,
            "plan": result.plan.__dict__ if result.plan else None,
            "messages": result.messages,
            "raw_response": result.raw_response,
        },
    )


@router.post("/v1/chat/completions")
async def openai_chat_completions(payload: dict[str, Any]):
    try:
        if payload.get("stream") is True:
            stream_iter = (
                submit_agent_job_and_stream(
                    payload=payload,
                    endpoint="/v1/chat/completions",
                )
                if QUEUE_ENABLED
                else stream_agent_from_openai_payload_direct(payload)
            )

            return StreamingResponse(
                stream_iter,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        if QUEUE_ENABLED:
            return await submit_agent_job_and_wait(
                payload=payload,
                endpoint="/v1/chat/completions",
            )

        result = await run_agent_from_openai_payload_direct(payload)

        if result.raw_response is not None:
            raw = result.raw_response
            raw.setdefault("backend", {})
            raw["backend"].update(
                {
                    "conversation_id": result.conversation_id,
                    "tool_rounds": result.tool_rounds,
                    "plan": result.plan.__dict__ if result.plan else None,
                    "queue_enabled": False,
                }
            )
            return raw

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "No raw response produced by backend orchestrator.",
                    "type": "backend_error",
                }
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": str(exc),
                    "type": "backend_exception",
                }
            },
        )
