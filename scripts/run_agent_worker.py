from __future__ import annotations

import asyncio
import json
import signal
import time
import traceback
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from prometheus_client import start_http_server

from inference.config import (
    KAFKA_BATCH_SIZE,
    KAFKA_BATCH_WAIT_MS,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_REQUEST_TOPIC,
    KAFKA_RESPONSE_TOPIC,
    KAFKA_WORKER_CONCURRENCY,
    KAFKA_WORKER_GROUP,
    WORKER_METRICS_ENABLED,
    WORKER_METRICS_PORT,
)
from serving.orchestration.agent_loop import run_agent_from_openai_payload_direct, stream_agent_from_openai_payload_direct


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


async def build_openai_response(
    *,
    payload: dict[str, Any],
    endpoint: str,
) -> dict[str, Any]:
    result = await run_agent_from_openai_payload_direct(payload)

    if result.raw_response is None:
        raise RuntimeError("No raw response produced by backend orchestrator.")

    raw = result.raw_response
    raw.setdefault("backend", {})
    raw["backend"].update(
        {
            "conversation_id": result.conversation_id,
            "tool_rounds": result.tool_rounds,
            "plan": result.plan.__dict__ if result.plan else None,
            "queue_enabled": True,
            "worker_endpoint": endpoint,
        }
    )

    return raw




async def stream_openai_response(
    *,
    payload: dict[str, Any],
    endpoint: str,
    job_id: str,
    producer: AIOKafkaProducer,
) -> None:
    """Run the agent in streaming mode and publish each SSE chunk to Kafka."""
    async for chunk in stream_agent_from_openai_payload_direct(payload):
        await producer.send_and_wait(
            KAFKA_RESPONSE_TOPIC,
            key=job_id,
            value={
                "ok": True,
                "job_id": job_id,
                "stream": True,
                "done": False,
                "chunk": chunk,
                "finished_at": None,
            },
        )

    await producer.send_and_wait(
        KAFKA_RESPONSE_TOPIC,
        key=job_id,
        value={
            "ok": True,
            "job_id": job_id,
            "stream": True,
            "done": True,
            "finished_at": time.time(),
        },
    )

async def handle_job(
    *,
    job: dict[str, Any],
    producer: AIOKafkaProducer,
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore:
        job_id = str(job.get("job_id", ""))
        endpoint = str(job.get("endpoint", "/v1/chat/completions"))
        payload = job.get("payload", {})

        print(
            f"[agent-worker] handling job_id={job_id} endpoint={endpoint}",
            flush=True,
        )

        if not job_id:
            print("[agent-worker] skipped job without job_id", flush=True)
            return

        try:
            if not isinstance(payload, dict):
                raise ValueError("Kafka job payload must be a dict.")

            if bool(job.get("stream")) or bool(payload.get("stream")):
                print(f"[agent-worker] streaming job job_id={job_id}", flush=True)
                await stream_openai_response(
                    payload=payload,
                    endpoint=endpoint,
                    job_id=job_id,
                    producer=producer,
                )
                print(f"[agent-worker] stream success job_id={job_id}", flush=True)
                return

            result = await build_openai_response(
                payload=payload,
                endpoint=endpoint,
            )

            response = {
                "ok": True,
                "job_id": job_id,
                "result": result,
                "finished_at": time.time(),
            }

            print(f"[agent-worker] job success job_id={job_id}", flush=True)

        except Exception as exc:
            response = {
                "ok": False,
                "job_id": job_id,
                "stream": bool(job.get("stream")) or bool(payload.get("stream")),
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "finished_at": time.time(),
            }

            print(
                f"[agent-worker] job error job_id={job_id}: {exc}\n"
                f"{traceback.format_exc()}",
                flush=True,
            )

        metadata = await producer.send_and_wait(
            KAFKA_RESPONSE_TOPIC,
            key=job_id,
            value=response,
        )

        print(
            f"[agent-worker] response sent job_id={job_id} "
            f"topic={metadata.topic} partition={metadata.partition} offset={metadata.offset}",
            flush=True,
        )


async def main() -> None:
    if WORKER_METRICS_ENABLED:
        start_http_server(WORKER_METRICS_PORT)
        print(
            f"[agent-worker] metrics server started on :{WORKER_METRICS_PORT}",
            flush=True,
        )

    stop_event = asyncio.Event()

    def request_stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    consumer = AIOKafkaConsumer(
        KAFKA_REQUEST_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_WORKER_GROUP,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        key_deserializer=_key_deserializer,
        value_deserializer=_json_deserializer,
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        key_serializer=_key_serializer,
        value_serializer=_json_serializer,
        linger_ms=5,
        acks="all",
    )

    semaphore = asyncio.Semaphore(KAFKA_WORKER_CONCURRENCY)
    running_tasks: set[asyncio.Task] = set()

    print(
        f"[agent-worker] starting | bootstrap={KAFKA_BOOTSTRAP_SERVERS} "
        f"request_topic={KAFKA_REQUEST_TOPIC} "
        f"response_topic={KAFKA_RESPONSE_TOPIC} "
        f"group_id={KAFKA_WORKER_GROUP}",
        flush=True,
    )

    await consumer.start()
    await producer.start()

    print(
        f"[agent-worker] started | batch_size={KAFKA_BATCH_SIZE} "
        f"wait_ms={KAFKA_BATCH_WAIT_MS} "
        f"concurrency={KAFKA_WORKER_CONCURRENCY}",
        flush=True,
    )

    try:
        while not stop_event.is_set():
            batches = await consumer.getmany(
                timeout_ms=KAFKA_BATCH_WAIT_MS,
                max_records=KAFKA_BATCH_SIZE,
            )

            total = sum(len(messages) for messages in batches.values())

            if total:
                print(f"[agent-worker] polled {total} jobs", flush=True)

            for _, messages in batches.items():
                for message in messages:
                    task = asyncio.create_task(
                        handle_job(
                            job=message.value,
                            producer=producer,
                            semaphore=semaphore,
                        )
                    )
                    running_tasks.add(task)
                    task.add_done_callback(running_tasks.discard)

            await asyncio.sleep(0)

    finally:
        print("[agent-worker] stopping...", flush=True)

        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)

        await consumer.stop()
        await producer.stop()

        print("[agent-worker] stopped", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
