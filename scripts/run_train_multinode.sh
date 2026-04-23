#!/usr/bin/env bash
set -euo pipefail

MASTER_ADDR=${MASTER_ADDR:?MASTER_ADDR is required}
MASTER_PORT=${MASTER_PORT:-29500}
NODE_RANK=${NODE_RANK:?NODE_RANK is required}
NNODES=${NNODES:-2}
GPUS_PER_NODE=${GPUS_PER_NODE:-1}

export NCCL_DEBUG=${NCCL_DEBUG:-INFO}
export TORCH_DISTRIBUTED_DEBUG=${TORCH_DISTRIBUTED_DEBUG:-DETAIL}
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-eth0}
export CUDA_DEVICE_MAX_CONNECTIONS=${CUDA_DEVICE_MAX_CONNECTIONS:-1}
export PYTHONUNBUFFERED=1

echo "[train-ddp] MASTER_ADDR=${MASTER_ADDR}"
echo "[train-ddp] MASTER_PORT=${MASTER_PORT}"
echo "[train-ddp] NODE_RANK=${NODE_RANK}"
echo "[train-ddp] NNODES=${NNODES}"
echo "[train-ddp] GPUS_PER_NODE=${GPUS_PER_NODE}"

python -m torch.distributed.run \
  --nnodes="${NNODES}" \
  --nproc_per_node="${GPUS_PER_NODE}" \
  --node_rank="${NODE_RANK}" \
  --master_addr="${MASTER_ADDR}" \
  --master_port="${MASTER_PORT}" \
  scripts/run_train.py
