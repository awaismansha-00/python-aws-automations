import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://example.com"
EXPECTED_VERSION = "1.2.0"

CONNECT_TIMEOUT = 3
READ_TIMEOUT = 10

RETRY_COUNT = 3
RETRY_BACKOFF_SECONDS = 2

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "deployment-verifier/1.0",
}

ENDPOINTS = {
    "health": "/health",
    "readiness": "/ready",
    "version": "/version",
}


def create_session():
    retry_policy = Retry(
        total=RETRY_COUNT,
        connect=RETRY_COUNT,
        read=RETRY_COUNT,
        status=RETRY_COUNT,
        backoff_factor=RETRY_BACKOFF_SECONDS,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(
        max_retries=retry_policy
    )

    session = requests.Session()
    session.headers.update(HEADERS)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def make_request(session, endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"

    response = session.get(
        url,
        params=params,
        timeout=(
            CONNECT_TIMEOUT,
            READ_TIMEOUT,
        ),
        verify=True,
    )

    response.raise_for_status()

    return response


def check_health(session):
    print("\nChecking health endpoint...")

    response = make_request(
        session,
        ENDPOINTS["health"],
    )

    data = response.json()

    status = data.get("status")

    print(f"Health status: {status}")
    print(
        f"Response time: "
        f"{response.elapsed.total_seconds():.2f}s"
    )

    return status == "healthy"


def check_readiness(session):
    print("\nChecking readiness endpoint...")

    response = make_request(
        session,
        ENDPOINTS["readiness"],
        params={
            "include_dependencies": "true",
        },
    )

    data = response.json()

    ready = data.get("ready", False)

    print(f"Application ready: {ready}")

    dependencies = data.get(
        "dependencies",
        {},
    )

    for dependency, status in dependencies.items():
        print(
            f"  {dependency}: {status}"
        )

    return ready is True


def check_version(session):
    print("\nChecking deployed version...")

    response = make_request(
        session,
        ENDPOINTS["version"],
    )

    data = response.json()

    deployed_version = data.get("version")

    print(f"Expected version: {EXPECTED_VERSION}")
    print(f"Deployed version: {deployed_version}")

    return deployed_version == EXPECTED_VERSION


def verify_deployment():
    results = {
        "health": False,
        "readiness": False,
        "version": False,
    }

    with create_session() as session:
        try:
            results["health"] = check_health(
                session
            )

            results["readiness"] = check_readiness(
                session
            )

            results["version"] = check_version(
                session
            )

        except requests.Timeout:
            print(
                "\nFAILED: Request timed out."
            )

        except requests.ConnectionError as error:
            print(
                f"\nFAILED: Connection error: {error}"
            )

        except requests.HTTPError as error:
            status_code = (
                error.response.status_code
                if error.response
                else "Unknown"
            )

            print(
                f"\nFAILED: HTTP error "
                f"{status_code}: {error}"
            )

        except requests.JSONDecodeError:
            print(
                "\nFAILED: Endpoint returned "
                "invalid JSON."
            )

        except requests.RequestException as error:
            print(
                f"\nFAILED: Request failed: {error}"
            )

    return results


def display_summary(results):
    print("\n" + "=" * 60)
    print("DEPLOYMENT VERIFICATION SUMMARY")
    print("=" * 60)

    for check_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"

        print(
            f"{check_name.title():<20} {status}"
        )

    deployment_passed = all(
        results.values()
    )

    print("-" * 60)

    if deployment_passed:
        print("Deployment verification PASSED.")
        return 0

    print("Deployment verification FAILED.")
    return 1


def main():
    print("DEPLOYMENT VERIFICATION")
    print(f"Application: {BASE_URL}")

    results = verify_deployment()
    exit_code = display_summary(results)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()