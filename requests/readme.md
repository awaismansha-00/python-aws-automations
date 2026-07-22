# DevOps API Automation with Requests

This folder contains Python scripts for automating HTTP and API-based DevOps workflows using the Requests library.

The scripts focus on practical use cases involving:

- Application deployment verification
- GitHub repository auditing
- Prometheus-based deployment health checks
- Build artifact downloads
- API authentication
- Retry handling
- CI/CD exit codes

## Requirements

Install Requests:

pip install requests

Some scripts also use retry support from urllib3, which is installed with Requests.

Authentication tokens should be passed through environment variables rather than hard-coded inside scripts.

Example:

export GITHUB_TOKEN="your-token"

---

## Scripts

### deployment_verifier.py

Verifies an application after deployment.

The script checks:

- Health endpoint
- Readiness endpoint
- Dependency readiness
- Version endpoint
- Expected application version
- HTTP response status
- Response time
- JSON response content

The default endpoints are:

/health
/ready
/version

The script uses:

- GET requests
- Query parameters
- JSON response parsing
- Shared request headers
- Requests sessions
- Connection and read timeouts
- Retry handling
- TLS certificate verification
- Exception handling
- CI/CD exit codes

Example readiness request:

/ready?include_dependencies=true

The script expects responses similar to:

Health response:

{
  "status": "healthy"
}

Readiness response:

{
  "ready": true,
  "dependencies": {
    "database": "healthy",
    "redis": "healthy"
  }
}

Version response:

{
  "version": "1.2.0"
}

The script exits with:

0 = all deployment checks passed
1 = one or more checks failed

This makes it suitable for use after deployment in GitHub Actions or another CI/CD pipeline.

Important limitation:

The endpoint paths and JSON fields must be updated to match the target application.

---

### github_repository_auditor.py

Audits repositories through the GitHub REST API.

It checks:

- Repository visibility
- Archived repositories
- Disabled repositories
- Default branch
- Open issues
- Default-branch protection
- Recent GitHub Actions workflow runs
- Recent failed, cancelled or timed-out workflow runs

The script demonstrates:

- Bearer-token authentication
- Shared headers
- Requests sessions
- GET requests
- Query parameters
- Pagination
- GitHub Link headers
- Rate-limit headers
- Nested JSON parsing
- HTTP status handling
- CI/CD exit codes

The script reads the GitHub token from:

GITHUB_TOKEN

Example:

export GITHUB_TOKEN="your-token"

The owner type can be configured as:

OWNER_TYPE = "user"

or:

OWNER_TYPE = "org"

The script handles pagination through the GitHub response Link header.

It also reads rate-limit values such as:

X-RateLimit-Remaining
X-RateLimit-Reset

Important limitations:

- A 404 response from the branch-protection endpoint may mean protection is missing, but it may also mean that the token does not have permission to inspect it.
- The token should have only the minimum read permissions required.
- Open issue counts may also include pull requests depending on the GitHub API field used.
- Rate limits still apply even when authentication is configured.

---

### prometheus_health_gate.py

Queries Prometheus metrics and decides whether a deployment should pass or fail.

The script checks metrics such as:

- HTTP 5xx error rate
- p95 request latency
- Unavailable Kubernetes replicas
- Prometheus targets that are down

Example thresholds:

Maximum error rate: 2%
Maximum p95 latency: 0.5 seconds
Unavailable replicas: 0
Down targets: 0

The script uses the Prometheus instant query API:

/api/v1/query

PromQL expressions are sent as query parameters.

Example:

params={
    "query": query
}

The script demonstrates:

- GET requests
- Query parameters
- Optional bearer-token authentication
- JSON response parsing
- Timeouts
- Retries
- Error handling
- Threshold evaluation
- CI/CD exit codes

The script exits with:

0 = all metrics passed
1 = one or more metrics failed or returned no data

This allows it to act as an observability-based deployment gate in CI/CD.

Important limitations:

- PromQL queries must be changed to match the actual metric names exposed by the application.
- No data is treated as a failure.
- Thresholds are custom operational policies and are not universal defaults.
- A single instant query may not represent the full health of an application.
- Authentication depends on how the Prometheus server is exposed.

---

### artifact_downloader.py

Downloads a build artifact through HTTP or an authenticated API.

The script supports:

- Bearer-token authentication
- Streaming downloads
- Binary file handling
- Retry handling
- Connection and read timeouts
- TLS verification
- Download progress
- SHA-256 checksum calculation
- Optional checksum validation
- Temporary partial files
- CI/CD exit codes

The script reads the authentication token from:

ARTIFACT_API_TOKEN

Example:

export ARTIFACT_API_TOKEN="your-token"

The artifact is downloaded in chunks instead of being loaded completely into memory.

Example chunk size:

CHUNK_SIZE = 1024 * 1024

This represents 1 MB per chunk.

The script writes the download to a temporary file such as:

myapp.tar.gz.part

The temporary file is renamed to the final filename only after:

- The download completes
- The file is not empty
- The checksum matches when verification is enabled

The script exits with:

0 = download and validation succeeded
1 = download or validation failed

Important limitations:

- The expected checksum must come from a trusted source.
- If EXPECTED_SHA256 is empty, checksum comparison is skipped.
- Download retries should be reviewed carefully for very large files.
- The server may not provide a Content-Length header, so progress percentage may not always be available.

---

## Running the Scripts

Run the deployment verifier:

python3 deployment_verifier.py

Run the GitHub repository auditor:

python3 github_repository_auditor.py

Run the Prometheus health gate:

python3 prometheus_health_gate.py

Run the artifact downloader:

python3 artifact_downloader.py

Review all configuration variables at the top of each script before running it.

---

## Suggested Folder Structure

requests/
├── artifact_downloader.py
├── deployment_verifier.py
├── github_repository_auditor.py
├── prometheus_health_gate.py
└── README.md

---

## Common Requests Features Used

### requests.get()

Sends an HTTP GET request.

Example:

response = requests.get(
    "https://example.com/health",
    timeout=10
)

---

### requests.post()

Sends an HTTP POST request.

Example:

response = requests.post(
    "https://example.com/api/report",
    json={
        "status": "passed"
    },
    timeout=10
)

---

### Query parameters

Requests converts a Python dictionary into URL query parameters.

Example:

response = session.get(
    url,
    params={
        "branch": "main",
        "per_page": 100
    }
)

This becomes:

?branch=main&per_page=100

---

### JSON responses

JSON API responses can be converted into Python dictionaries and lists.

Example:

data = response.json()

---

### Headers

Headers are used for authentication, content type and API versions.

Example:

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

---

### Sessions

A Requests session stores shared configuration and reuses HTTP connections.

Example:

session = requests.Session()

session.headers.update({
    "Authorization": f"Bearer {token}"
})

Sessions are useful when making several requests to the same API.

---

### Timeouts

Production scripts should always configure timeouts.

Example:

timeout=(3, 15)

This means:

3 seconds for connection
15 seconds for response data

Requests does not apply a default timeout automatically.

---

### Retries

Retries are configured using HTTPAdapter and Retry.

They are useful for temporary failures such as:

429
500
502
503
504

Retries should usually be limited to safe and repeatable requests such as GET.

---

### Exception handling

Common Requests exceptions include:

requests.Timeout
requests.ConnectionError
requests.HTTPError
requests.JSONDecodeError
requests.RequestException

These allow scripts to handle failures cleanly instead of crashing with a long traceback.

---

### TLS verification

Requests verifies HTTPS certificates by default.

Example:

verify=True

Avoid:

verify=False

Disabling verification can expose the connection to man-in-the-middle attacks.

---

### Streaming downloads

Large files can be downloaded without loading the entire response into memory.

Example:

with requests.get(
    url,
    stream=True,
    timeout=30
) as response:
    for chunk in response.iter_content(
        chunk_size=8192
    ):
        file.write(chunk)

---

### CI/CD exit codes

Scripts use:

sys.exit(0)

for success, and:

sys.exit(1)

for failure.

This allows GitHub Actions and other CI/CD systems to pass or fail a job based on the script result.

---

## What These Scripts Demonstrate

The scripts demonstrate practical Requests usage for DevOps, including:

- API authentication
- GET requests
- Query parameters
- JSON parsing
- Shared headers
- Sessions
- Connection reuse
- Timeouts
- Retries
- Exception handling
- Pagination
- Rate-limit awareness
- Streaming downloads
- Binary file handling
- Checksum validation
- TLS verification
- CI/CD exit codes
- Deployment verification
- GitHub API automation
- Prometheus API automation

---

## Security and Safety Notes

- Never hard-code API tokens in scripts.
- Use environment variables or a secret-management system.
- Use least-privilege API tokens.
- Keep TLS verification enabled.
- Always configure request timeouts.
- Do not retry unsafe POST or DELETE operations automatically without understanding the consequences.
- Respect API rate limits.
- Validate JSON fields before using them.
- Do not log authentication headers or tokens.
- Verify artifact checksums using a trusted checksum source.
- Test scripts against non-production services first.
- Review exit-code behaviour before adding a script as a required CI/CD gate.

---

## Limitations

- Requests is synchronous and blocking.
- Large numbers of concurrent API calls may require another library such as httpx or aiohttp.
- API response formats can change between versions.
- Authentication requirements differ between systems.
- Retry behaviour does not guarantee that an API will become available.
- The scripts depend on the availability of external services.
- API permissions may prevent some checks from running.
- The Prometheus script depends on environment-specific metric names.
- The GitHub auditor may produce incomplete results when the token lacks permission.
- The deployment verifier depends on the target application exposing suitable health, readiness and version endpoints.