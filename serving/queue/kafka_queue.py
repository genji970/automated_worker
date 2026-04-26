from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from inference.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_REQUEST_TIMEOUT_SEC,
    KAFKA_REQUEST_TOPIC,
    KAFKA_RESPONSE_TOPIC,
)


def _json_serializer(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _json_deserializer(value: bytes) -> dict[str, Any]:
    return json.loads(value.decode("utf-8"))


def _key_serializer(value: str) -> bytes:
    return str(value).encode("utf-8")


def _key_deserializer(value: bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8")


async def _start_job_in_kafka(
    *,
    payload: dict[str, Any],
    endpoint: str,
    stream: bool,
) -> tuple[str, AIOKafkaProducer, AIOKafkaConsumer]:
    job_id = str(uuid.uuid4())

    print(
        f"[backend-kafka] start job_id={job_id} stream={stream} "
        f"bootstrap={KAFKA_BOOTSTRAP_SERVERS} "
        f"request_topic={KAFKA_REQUEST_TOPIC} "
        f"response_topic={KAFKA_RESPONSE_TOPIC}",
        flush=True,
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        key_serializer=_key_serializer,
        value_serializer=_json_serializer,
        linger_ms=5,
        acks="all",
    )

    consumer = AIOKafkaConsumer(
        KAFKA_RESPONSE_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"backend-response-{job_id}",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        key_deserializer=_key_deserializer,
        value_deserializer=_json_deserializer,
    )

    await producer.start()
    await consumer.start()

    request = {
        "job_id": job_id,
        "endpoint": endpoint,
        "payload": payload,
        "stream": stream,
        "created_at": time.time(),
    }

    metadata = await producer.send_and_wait(
        KAFKA_REQUEST_TOPIC,
        key=job_id,
        value=request,
    )

    print(
        f"[backend-kafka] sent job_id={job_id} stream={stream} "
        f"topic={metadata.topic} partition={metadata.partition} offset={metadata.offset}",
        flush=True,
    )

    return job_id, producer, consumer


async def submit_agent_job_and_wait(
    *,
    payload: dict[str, Any],
    endpoint: str,
    timeout_sec: float = KAFKA_REQUEST_TIMEOUT_SEC,
) -> dict[str, Any]:
    job_id, producer, consumer = await _start_job_in_kafka(
        payload=payload,
        endpoint=endpoint,
        stream=False,
    )

    try:
        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()

            try:
                batches = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=1000, max_records=100),
                    timeout=max(1.0, remaining),
                )
            except asyncio.TimeoutError:
                break

            for _, messages in batches.items():
                for message in messages:
                    if message.key != job_id:
                        continue

                    response = message.value

                    if response.get("ok"):
                        return response["result"]

                    raise RuntimeError(response.get("error", "Unknown worker error"))

        raise TimeoutError(f"Timed out waiting for Kafka response job_id={job_id}")

    finally:
        try:
            await consumer.stop()
        finally:
            await producer.stop()


async def submit_agent_job_and_stream(
    *,
    payload: dict[str, Any],
    endpoint: str,
    timeout_sec: float = KAFKA_REQUEST_TIMEOUT_SEC,
) -> AsyncIterator[str]:
    """Submit a streaming job to Kafka and relay worker SSE chunks."""
    stream_payload = dict(payload)
    stream_payload["stream"] = True

    job_id, producer, consumer = await _start_job_in_kafka(
        payload=stream_payload,
        endpoint=endpoint,
        stream=True,
    )

    try:
        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()

            try:
                batches = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=1000, max_records=100),
                    timeout=max(1.0, remaining),
                )
            except asyncio.TimeoutError:
                break

            for _, messages in batches.items():
                for message in messages:
                    if message.key != job_id:
                        continue

                    response = message.value

                    if not response.get("ok"):
                        error_chunk = {
                            "object": "chat.completion.chunk",
                            "error": {
                                "message": response.get("error", "Unknown worker error"),
                                "type": "worker_stream_error",
                            },
                            "backend": {
                                "queue_enabled": True,
                                "job_id": job_id,
                                "streamed": True,
                            },
                        }
                        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    if response.get("done"):
                        return

                    chunk = response.get("chunk")
                    if isinstance(chunk, str):
                        yield chunk

        timeout_chunk = {
            "object": "chat.completion.chunk",
            "error": {
                "message": f"Timed out waiting for Kafka stream job_id={job_id}",
                "type": "backend_stream_timeout",
            },
            "backend": {
                "queue_enabled": True,
                "job_id": job_id,
                "streamed": True,
            },
        }
        yield f"data: {json.dumps(timeout_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    finally:
        try:
            await consumer.stop()
        finally:
            await producer.stop()


"""
→ backend가 Kafka agent.requests에 streaming job 전송
→ worker가 planner/tool 단계는 순차 처리
→ final-answer 단계만 stream=True로 vLLM 호출
→ worker가 토큰 chunk를 agent.responses로 전송
→ backend가 그 chunk를 SSE로 Open WebUI에 relay

"""