# llm_agent multinode full setup

이 템플릿은 아래를 기준으로 구성되어 있습니다.

- 분산학습: 2 nodes, 1 GPU per node, torch.distributed DDP
- 분산추론/서빙: Ray + vLLM, TP=1, PP=2
- backend: FastAPI /chat + tool loop
- frontend: Open WebUI docker image
- monitoring: Prometheus / Grafana / node-exporter / dcgm-exporter
- load test: JMeter

## 1. node1에서 Ray worker 시작
```bash
cd /workspace/llm_agent
bash scripts/run_vllm_ray_worker.sh
```

필수 환경변수:
```bash
export HEAD_IP=<node0_ip>
export RAY_PORT=6379
```

## 2. node0에서 Ray head + vLLM 시작
```bash
cd /workspace/llm_agent

export MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
export VLLM_API_KEY=local-dev-key
export VLLM_PORT=8000
export RAY_PORT=6379
export RAY_DASHBOARD_PORT=8265
export TENSOR_PARALLEL_SIZE=1
export PIPELINE_PARALLEL_SIZE=2
export RAY_HEAD_HOST=<node0_ip>

bash scripts/run_vllm_ray_head.sh
```

## 3. backend 시작
```bash
cd /workspace/llm_agent
export PYTHONPATH=$(pwd)
export VLLM_BASE_URL=http://127.0.0.1:8000/v1
export VLLM_API_KEY=local-dev-key
export BACKEND_HOST=0.0.0.0
export BACKEND_PORT=9000
python -m scripts.run_backend
```

## 4. frontend 실행
```bash
cd /workspace/llm_agent/compose
docker compose -f docker-compose.frontend.yml up -d
```

## 5. metrics 실행
```bash
cd /workspace/llm_agent/compose
docker compose -f docker-compose.metrics.yml up -d
```

## 6. backend 컨테이너로 실행하려면
```bash
cd /workspace/llm_agent/compose
docker compose -f docker-compose.backend.yml up --build -d
```

## 7. 분산학습 실행
node0:
```bash
export MASTER_ADDR=<node0_ip>
export MASTER_PORT=29500
export NODE_RANK=0
export NNODES=2
export GPUS_PER_NODE=1
bash scripts/run_train_multinode.sh
```

node1:
```bash
export MASTER_ADDR=<node0_ip>
export MASTER_PORT=29500
export NODE_RANK=1
export NNODES=2
export GPUS_PER_NODE=1
bash scripts/run_train_multinode.sh
```

## 8. 테스트
```bash
python scripts/test_client.py
```

## 9. 주의
- Open WebUI는 현재 vLLM OpenAI endpoint에 직접 연결됩니다.
- FastAPI backend는 커스텀 /chat 스키마이므로 Open WebUI에 직접 붙이려면 OpenAI-compatible proxy route를 따로 추가해야 합니다.
- Prometheus가 host.docker.internal을 긁도록 되어 있으므로 Linux Docker 환경에서 host-gateway 지원이 필요합니다.
