## Intro.
This project implements a local OpenAI-compatible agent backend connected to Open WebUI, vLLM, Kafka, and Gmail MCP tools.

The overall flow is:

```python
Open WebUI / curl
        ↓
FastAPI backend
        ↓
Kafka async queue
        ↓
Async agent worker
        ↓
Planner / tool-use / final-answer agents
        ↓
Gmail MCP tools + vLLM
```
A key part of the design is that the system uses asynchronous I/O throughout the serving path. The FastAPI backend does not directly block while waiting for model or tool responses. Instead, requests are submitted to Kafka, and an async worker consumes jobs concurrently. This lets multiple user requests overlap while waiting on vLLM generation, Gmail API calls, or MCP tool execution.

The worker uses async task dispatch so several jobs can be processed at the same time. This is important for vLLM because overlapping requests make it easier for vLLM to benefit from continuous batching. In other words, the system is not just a simple one-request-at-a-time chatbot wrapper; it is structured as an asynchronous queue-based serving pipeline.

The Gmail demo shows this architecture working end-to-end: the prompting user asks about their own Gmail inbox, the request goes through the backend and worker, the Gmail MCP tool retrieves the user’s mailbox data through OAuth, and the final answer summarizes the result without exposing the user’s email address.

## demo shot

<img width="1913" height="926" alt="Image" src="https://github.com/user-attachments/assets/a83bda11-def1-4c5c-832e-92f99c29007e" />

This demo shows the assistant accessing the **prompting user’s own Gmail account** through the local FastAPI backend and Gmail MCP tooling. The user asks for their first Gmail message while requesting that their email address not be mentioned, and the assistant retrieves the mailbox result and summarizes the message title/date/snippet without exposing the user’s address.

## Important
You have to change path `~/automated_worker` -> `~/backend_server` after `git clone this repo`.

## How to Create `credentials.json` for Gmail OAuth

```python
Follow these steps to create a Google OAuth JSON file and place it in this project.

## 1. Open Google Cloud Console

Go to:

https://console.cloud.google.com/

Log in with your Google account.

## 2. Create or Select a Project

Click the project selector at the top of the page.

Select project → New project

Example project name:

gmail-mcp-local

Create the project, then make sure it is selected.

## 3. Enable Gmail API

Go to:

APIs & Services → Library

Search for:

Gmail API

Click Gmail API, then click Enable.

## 4. Configure OAuth Consent Screen

Go to:

APIs & Services → OAuth consent screen

or, in the newer UI:

Google Auth Platform → Branding

Set:

User Type: External  
App name: gmail-mcp-local  
User support email: example@example.com  
Developer contact email: example@example.com

Save and continue.

## 5. Add Test User

If the app is in testing mode, only registered test users can log in.

Go to:

Google Auth Platform → Audience

or:

OAuth consent screen → Test users

Click Add users.

Add your Gmail address, for example:

example@example.com

Save.

## 6. Create OAuth Client

Go to:

Google Auth Platform → Clients

or:

APIs & Services → Credentials

Click:

Create client

or:

Create credentials → OAuth client ID

Choose:

Application type: Desktop app  
Name: gmail-mcp-local-client

Click Create.

## 7. Download JSON

After the OAuth client is created, click:

Download JSON

The downloaded file will look like:

client_secret_xxxxxxxxx.json

## 8. Rename the File

Rename the downloaded file to:

credentials.json

## 9. Move It to the Project Root

Place credentials.json in your local project root.

Example:

C:\path\to\your\project\credentials.json

The final structure should look like:

your_project/
  credentials.json
  serving/
  scripts/
  inference/

Check it with PowerShell:

cd C:\path\to\your\project
dir .\credentials.json

## 10. First Gmail OAuth Login

When you run the Gmail tool for the first time, a browser window will open.

Log in with your Google account and allow the requested permissions.

After success, you should see:

The authentication flow has completed. You may close this window.

Then the project will automatically create:

C:\path\to\your\project\state\token_gmail.pickle

Check it with PowerShell:

dir C:\path\to\your\project\state\token_gmail.pickle
```

## How to run backend
```python
cd /path/to/backend_server

VLLM_BASE_URL="http://127.0.0.1:8000/v1" \
VLLM_API_KEY="local-dev-key" \
MODEL_NAME="Qwen/Qwen2.5-7B-Instruct" \
BACKEND_HOST="127.0.0.1" \
BACKEND_PORT="9000" \
# backend queue mode
export QUEUE_ENABLED=true
export KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
bash scripts/run_backend_to_gpu.sh
```

## How to run kafka for queue 
```python
cd /path/to/backend_server

sudo systemctl start docker
sudo systemctl enable docker

docker compose -f docker-compose.kafka.yml down
docker compose -f docker-compose.kafka.yml up -d
```

## Env setting for mcp 
```python
cd /path/to/backend_server

export GOOGLE_CREDENTIALS_PATH="/path/to/backend_server/credentials.json"
export GOOGLE_TOKEN_PATH="/path/to/backend_server/state/token_gmail.pickle"

export TOOL_BACKEND="mcp"
export MCP_SERVER_COMMAND="python"
export MCP_SERVER_ARGS="-m serving.tools.mcp.server"
```

## How to run agent worker
```python
cd /path/to/backend_server

export KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:9092"

export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_API_KEY="local-dev-key"
export MODEL_NAME="Qwen/Qwen2.5-7B-Instruct"

export DEFAULT_MAX_TOKENS="512"
export PYTHONPATH="$(pwd)"

python -m scripts.run_agent_worker
```

## How to run open webui
```python
cd /path/to/backend_server

docker rm -f open-webui || true

docker run -d \
  --name open-webui \
  --restart always \
  -p 8080:8080 \
  -e OPENAI_API_BASE_URL="http://host.docker.internal:9000/v1" \
  -e OPENAI_API_BASE_URLS="http://host.docker.internal:9000/v1" \
  -e OPENAI_API_KEY="local-dev-key" \
  -e OPENAI_API_KEYS="local-dev-key" \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
```
## How to run VLLM

```python
cd /path/to/backend_server/vllm_server
pip install -r requirements.txt

CUDA_VISIBLE_DEVICES=0 \
TENSOR_PARALLEL_SIZE=1 \
PIPELINE_PARALLEL_SIZE=1 \
bash scripts/run_single_node.sh
```

## Further plan
`parallel training/inference with ray.`
`training.`
`additional tool for gmail.`
`prompt opt`

## Contribution
We welcome your contribution to this repo.

## Acknowledgement

This project uses the following open-source projects:

- Qwen2.5-7B-Instruct by Qwen, licensed under Apache-2.0.
- vLLM, licensed under Apache-2.0.
- Apache Kafka, licensed under Apache-2.0.
