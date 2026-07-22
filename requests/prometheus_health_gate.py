import os
import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROMETHEUS_URL = "https://prometheus.example.com"

CONNECT_TIMEOUT = 3
READ_TIMEOUT = 15
RETRY_COUNT = 3

# Optional authentication token.
PROMETHEUS_TOKEN = os.getenv("PROMETHEUS_TOKEN")

THRESHOLDS = {
    "error_rate": 2.0,           # Maximum 2%
    "p95_latency": 0.5,          # Maximum 0.5 seconds
    "unavailable_replicas": 0,
    "down_targets": 0,
}

QUERIES = {
    "error_rate": (
        '100 * sum(rate(http_requests_total{status=~"5.."}[5m])) '
        '/ sum(rate(http_requests_total[5m]))'
    ),
    "p95_latency": (
        "histogram_quantile("
        "0.95, "
        "sum(rate(http_request_duration_seconds_bucket[5m])) "
        "by (le)"
        ")"
    ),
    "unavailable_replicas": (
        "sum(kube_deployment_status_replicas_unavailable)"
    ),
    "down_targets": (
        "count(up == 0)"
    ),
}


def create_session():
    retry_policy = Retry(
        total=RETRY_COUNT,
        connect=RETRY_COUNT,
        read=RETRY_COUNT,
        status=RETRY_COUNT,
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=["GET"],
    )

    session = requests.Session()

    session.mount(
        "https://",
        HTTPAdapter(max_retries=retry_policy),
    )

    session.mount(
        "http://",
        HTTPAdapter(max_retries=retry_policy),
    )

    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "prometheus-health-gate/1.0",
        }
    )

    if PROMETHEUS_TOKEN:
        session.headers.update(
            {
                "Authorization": (
                    f"Bearer {PROMETHEUS_TOKEN}"
                )
            }
        )

    return session


def query_prometheus(session, query):
    url = f"{PROMETHEUS_URL}/api/v1/query"

    response = session.get(
        url,
        params={
            "query": query,
        },
        timeout=(
            CONNECT_TIMEOUT,
            READ_TIMEOUT,
        ),
        verify=True,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(
            data.get(
                "error",
                "Prometheus query failed",
            )
        )

    result = (
        data.get("data", {})
        .get("result", [])
    )

    if not result:
        return None

    value = result[0].get("value")

    if not value or len(value) < 2:
        return None

    return float(value[1])


def evaluate_metric(metric_name, value):
    threshold = THRESHOLDS[metric_name]

    if value is None:
        return False, "NO DATA"

    passed = value <= threshold

    status = "PASSED" if passed else "FAILED"

    return passed, status


def format_value(metric_name, value):
    if value is None:
        return "No data"

    if metric_name == "error_rate":
        return f"{value:.2f}%"

    if metric_name == "p95_latency":
        return f"{value:.3f} seconds"

    return f"{value:.0f}"


def display_result(
    metric_name,
    value,
    passed,
    status,
):
    readable_name = metric_name.replace(
        "_",
        " ",
    ).title()

    print("\n" + "-" * 65)
    print(f"Metric: {readable_name}")
    print(f"Value: {format_value(metric_name, value)}")
    print(
        f"Threshold: "
        f"{format_value(metric_name, THRESHOLDS[metric_name])}"
    )
    print(f"Result: {status}")

    if not passed and value is None:
        print(
            "Reason: Prometheus returned no matching data."
        )


def run_health_gate():
    results = {}

    with create_session() as session:
        for metric_name, query in QUERIES.items():
            try:
                value = query_prometheus(
                    session,
                    query,
                )

                passed, status = evaluate_metric(
                    metric_name,
                    value,
                )

                results[metric_name] = passed

                display_result(
                    metric_name,
                    value,
                    passed,
                    status,
                )

            except requests.Timeout:
                print(
                    f"\n{metric_name}: FAILED — "
                    "Prometheus request timed out."
                )

                results[metric_name] = False

            except requests.ConnectionError as error:
                print(
                    f"\n{metric_name}: FAILED — "
                    f"Connection error: {error}"
                )

                results[metric_name] = False

            except requests.HTTPError as error:
                status_code = (
                    error.response.status_code
                    if error.response is not None
                    else "Unknown"
                )

                print(
                    f"\n{metric_name}: FAILED — "
                    f"HTTP {status_code}"
                )

                results[metric_name] = False

            except (
                requests.JSONDecodeError,
                requests.RequestException,
                RuntimeError,
                ValueError,
            ) as error:
                print(
                    f"\n{metric_name}: FAILED — {error}"
                )

                results[metric_name] = False

    return results


def display_summary(results):
    print("\n" + "=" * 65)
    print("PROMETHEUS DEPLOYMENT HEALTH GATE")
    print("=" * 65)

    for metric_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"

        print(
            f"{metric_name.replace('_', ' ').title():<30}"
            f"{status}"
        )

    health_gate_passed = (
        len(results) == len(QUERIES)
        and all(results.values())
    )

    print("-" * 65)

    if health_gate_passed:
        print("Deployment health gate PASSED.")
        return 0

    print("Deployment health gate FAILED.")
    return 1


def main():
    print(f"Prometheus server: {PROMETHEUS_URL}")

    results = run_health_gate()
    exit_code = display_summary(results)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()