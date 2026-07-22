import os
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


GITHUB_API_URL = "https://api.github.com"
GITHUB_OWNER = "awaismansha-00"

# Use "user" for a personal account or "org" for an organisation.
OWNER_TYPE = "user"

REQUEST_TIMEOUT = (3, 15)
PER_PAGE = 100

# Read the token securely from an environment variable.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def create_session():
    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(
        max_retries=retry_policy
    )

    session = requests.Session()

    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-repository-auditor/1.0",
        }
    )

    session.mount("https://", adapter)

    return session


def check_rate_limit(response):
    remaining = response.headers.get(
        "X-RateLimit-Remaining"
    )

    reset_time = response.headers.get(
        "X-RateLimit-Reset"
    )

    if remaining is not None:
        print(
            f"GitHub API requests remaining: {remaining}"
        )

    if remaining == "0" and reset_time:
        wait_seconds = max(
            int(reset_time) - int(time.time()),
            0,
        )

        raise RuntimeError(
            f"GitHub API rate limit reached. "
            f"Try again in approximately "
            f"{wait_seconds} seconds."
        )


def make_get_request(
    session,
    url,
    params=None,
    allow_not_found=False,
):
    response = session.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
        verify=True,
    )

    check_rate_limit(response)

    if allow_not_found and response.status_code == 404:
        return None

    response.raise_for_status()

    return response


def get_all_pages(session, url, params=None):
    results = []

    request_params = dict(params or {})
    request_params["per_page"] = PER_PAGE

    next_url = url

    while next_url:
        response = make_get_request(
            session,
            next_url,
            params=request_params,
        )

        data = response.json()

        if not isinstance(data, list):
            raise ValueError(
                f"Expected a list response from {next_url}"
            )

        results.extend(data)

        next_url = response.links.get(
            "next",
            {},
        ).get("url")

        # The next-page URL already contains its query string.
        request_params = None

    return results


def get_repositories(session):
    if OWNER_TYPE == "org":
        url = (
            f"{GITHUB_API_URL}/orgs/"
            f"{GITHUB_OWNER}/repos"
        )
    else:
        url = (
            f"{GITHUB_API_URL}/users/"
            f"{GITHUB_OWNER}/repos"
        )

    return get_all_pages(
        session,
        url,
        params={
            "type": "all",
            "sort": "updated",
            "direction": "desc",
        },
    )


def get_branch_protection(
    session,
    repository_name,
    default_branch,
):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{GITHUB_OWNER}/{repository_name}/"
        f"branches/{default_branch}/protection"
    )

    response = make_get_request(
        session,
        url,
        allow_not_found=True,
    )

    return response is not None


def get_recent_workflow_runs(
    session,
    repository_name,
):
    url = (
        f"{GITHUB_API_URL}/repos/"
        f"{GITHUB_OWNER}/{repository_name}/"
        f"actions/runs"
    )

    response = make_get_request(
        session,
        url,
        params={
            "per_page": 10,
        },
        allow_not_found=True,
    )

    if response is None:
        return []

    data = response.json()

    return data.get(
        "workflow_runs",
        [],
    )


def audit_repository(session, repository):
    repository_name = repository["name"]
    default_branch = repository.get(
        "default_branch",
        "main",
    )

    findings = []

    if repository.get("archived"):
        findings.append(
            "INFO: Repository is archived"
        )

    if repository.get("disabled"):
        findings.append(
            "HIGH: Repository is disabled"
        )

    if repository.get("visibility") == "public":
        findings.append(
            "INFO: Repository is public"
        )

    branch_protected = get_branch_protection(
        session,
        repository_name,
        default_branch,
    )

    if not branch_protected:
        findings.append(
            f"MEDIUM: Default branch "
            f"'{default_branch}' is not protected "
            "or protection could not be read"
        )

    workflow_runs = get_recent_workflow_runs(
        session,
        repository_name,
    )

    failed_runs = [
        run
        for run in workflow_runs
        if run.get("conclusion")
        in {
            "failure",
            "cancelled",
            "timed_out",
            "startup_failure",
        }
    ]

    if failed_runs:
        findings.append(
            f"MEDIUM: {len(failed_runs)} of the "
            f"last {len(workflow_runs)} workflow runs "
            "did not succeed"
        )

    print("\n" + "-" * 75)
    print(f"Repository: {repository['full_name']}")
    print(
        f"Visibility: "
        f"{repository.get('visibility', 'Unknown')}"
    )
    print(f"Default branch: {default_branch}")
    print(
        f"Open issues: "
        f"{repository.get('open_issues_count', 0)}"
    )
    print(f"Archived: {repository.get('archived')}")
    print(f"Branch protected: {branch_protected}")
    print(f"Recent workflow runs: {len(workflow_runs)}")
    print(f"Failed workflow runs: {len(failed_runs)}")

    if findings:
        print("Findings:")

        for finding in findings:
            print(f"  - {finding}")
    else:
        print("No findings.")

    return findings


def main():
    if not GITHUB_TOKEN:
        print(
            "GITHUB_TOKEN environment variable "
            "is not configured."
        )

        sys.exit(1)

    print("GITHUB REPOSITORY AUDITOR")
    print(f"Owner: {GITHUB_OWNER}")
    print(f"Owner type: {OWNER_TYPE}")

    repositories_with_findings = 0
    total_findings = 0

    try:
        with create_session() as session:
            repositories = get_repositories(session)

            if not repositories:
                print("No repositories found.")
                sys.exit(0)

            for repository in repositories:
                findings = audit_repository(
                    session,
                    repository,
                )

                if findings:
                    repositories_with_findings += 1
                    total_findings += len(findings)

        print("\n" + "=" * 75)
        print("AUDIT SUMMARY")
        print("=" * 75)
        print(
            f"Repositories scanned: "
            f"{len(repositories)}"
        )
        print(
            f"Repositories with findings: "
            f"{repositories_with_findings}"
        )
        print(f"Total findings: {total_findings}")

        # For learning, fail only when a disabled repository exists.
        # You can later define stricter CI/CD rules.
        sys.exit(0)

    except requests.Timeout:
        print("Audit failed: GitHub request timed out.")
        sys.exit(1)

    except requests.ConnectionError as error:
        print(f"Audit failed: Connection error: {error}")
        sys.exit(1)

    except requests.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else "Unknown"
        )

        print(
            f"Audit failed: GitHub returned "
            f"HTTP {status_code}: {error}"
        )

        sys.exit(1)

    except (
        requests.RequestException,
        RuntimeError,
        ValueError,
    ) as error:
        print(f"Audit failed: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()