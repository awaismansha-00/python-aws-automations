# DevOps API Automation with Requests

[← Back to Main README](../README.md)

This module demonstrates HTTP REST API automation, post-deployment health verification, Prometheus metric gates, and secure artifact downloading using **Requests**.

---

## ⚡ Setup & Authentication

1. **Install Dependencies**:
   ```bash
   pip install requests urllib3
   ```

2. **Environment Variables**:
   API credentials should be supplied via environment variables rather than hard-coded values:
   ```bash
   export GITHUB_TOKEN="ghp_your_personal_access_token"
   export ARTIFACT_API_TOKEN="your_artifact_token"
   ```

---

## 💡 Key Technical Patterns Demonstrated

### 1. HTTP Session Reuse (`requests.Session`)
Reuses underlying TCP connections across multiple API requests for improved performance and shared headers:
```python
import requests

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
})
```

### 2. Robust Timeout & Retry Policies
Production scripts should always specify explicit timeouts and retry logic for idempotent GET requests:
```python
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

response = session.get("https://api.example.com/health", timeout=(3, 10))
```

### 3. Memory-Efficient Streaming Downloads
`artifact_downloader.py` handles large file downloads by streaming chunks directly to disk instead of buffering the entire payload into RAM:
```python
with session.get(url, stream=True) as r:
    r.raise_for_status()
    with open("output.tar.gz.part", "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
```

### 4. Quality Gates & Exit Codes
All tools output standard CI/CD exit codes (`0` for success, `1` for failure/violations), enabling seamless integration into deployment pipelines (e.g., GitHub Actions, GitLab CI).