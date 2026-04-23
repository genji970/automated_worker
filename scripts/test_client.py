from __future__ import annotations

import requests

from inference.config import BACKEND_PORT


if __name__ == "__main__":
    payload = {
        "messages": [
            {"role": "user", "content": "What time is it in Asia/Seoul? Use tools if needed."}
        ],
        "temperature": 0.0,
        "max_tokens": 256,
    }
    response = requests.post(f"http://127.0.0.1:{BACKEND_PORT}/chat", json=payload, timeout=120)
    response.raise_for_status()
    print(response.json())
