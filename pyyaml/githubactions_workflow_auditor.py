import re
import sys
from pathlib import Path

import yaml


WORKFLOW_DIRECTORY = Path(".github/workflows")

SECURITY_TOOLS = [
    "gitleaks",
    "trivy",
    "checkov",
    "sonarqube",
    "codeql",
]

SENSITIVE_KEYWORDS = [
    "password",
    "secret",
    "token",
    "api_key",
    "access_key",
    "private_key",
]

AWS_CREDENTIAL_VARIABLES = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
]

FULL_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def load_workflow(file_path):
    with file_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def is_local_action(action_reference):
    return action_reference.startswith("./")


def is_docker_action(action_reference):
    return action_reference.startswith("docker://")


def is_action_pinned_to_sha(action_reference):
    if "@" not in action_reference:
        return False

    reference = action_reference.rsplit("@", 1)[1]

    return bool(FULL_SHA_PATTERN.fullmatch(reference))


def find_hardcoded_secrets(value, path=""):
    findings = []

    if isinstance(value, dict):
        for key, nested_value in value.items():
            current_path = f"{path}.{key}" if path else str(key)

            if any(
                keyword in str(key).lower()
                for keyword in SENSITIVE_KEYWORDS
            ):
                if isinstance(nested_value, str):
                    uses_github_secret = (
                        "${{ secrets." in nested_value
                        or "${{ github.token" in nested_value
                    )

                    if nested_value and not uses_github_secret:
                        findings.append(
                            f"HIGH: Possible hard-coded secret at "
                            f"'{current_path}'."
                        )

            findings.extend(
                find_hardcoded_secrets(
                    nested_value,
                    current_path,
                )
            )

    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(
                find_hardcoded_secrets(
                    item,
                    f"{path}[{index}]",
                )
            )

    return findings


def find_aws_credentials(workflow):
    findings = []

    workflow_text = str(workflow)

    for variable in AWS_CREDENTIAL_VARIABLES:
        if variable in workflow_text:
            findings.append(
                f"HIGH: Workflow references {variable}. "
                "Prefer GitHub OIDC and an IAM role."
            )

    return findings


def audit_action_reference(action_reference, job_name):
    findings = []

    if is_local_action(action_reference):
        return findings

    if is_docker_action(action_reference):
        findings.append(
            f"MEDIUM: Job '{job_name}' uses Docker action "
            f"'{action_reference}'. Verify the image is pinned "
            "to an immutable digest."
        )

        return findings

    if not is_action_pinned_to_sha(action_reference):
        findings.append(
            f"MEDIUM: Job '{job_name}' uses "
            f"'{action_reference}' without a full commit SHA."
        )

    return findings


def audit_job(job_name, job):
    findings = []

    if not isinstance(job, dict):
        return findings

    if "uses" in job:
        findings.extend(
            audit_action_reference(
                str(job["uses"]),
                job_name,
            )
        )

        return findings

    if "timeout-minutes" not in job:
        findings.append(
            f"LOW: Job '{job_name}' does not define "
            "timeout-minutes."
        )

    steps = job.get("steps", [])

    for step in steps:
        if not isinstance(step, dict):
            continue

        action_reference = step.get("uses")

        if action_reference:
            findings.extend(
                audit_action_reference(
                    str(action_reference),
                    job_name,
                )
            )

    return findings


def has_security_scanning(workflow):
    workflow_text = str(workflow).lower()

    detected_tools = [
        tool
        for tool in SECURITY_TOOLS
        if tool in workflow_text
    ]

    return detected_tools


def audit_workflow(file_path):
    print("\n" + "=" * 80)
    print(f"WORKFLOW: {file_path}")
    print("=" * 80)

    try:
        workflow = load_workflow(file_path)

    except yaml.YAMLError as error:
        print(f"HIGH: Invalid YAML syntax: {error}")
        return 1

    findings = []

    if not workflow.get("name"):
        findings.append(
            "LOW: Workflow does not define a name."
        )

    if "on" not in workflow and True not in workflow:
        findings.append(
            "HIGH: Workflow does not define a trigger."
        )

    if "permissions" not in workflow:
        findings.append(
            "MEDIUM: Workflow does not define top-level "
            "GITHUB_TOKEN permissions."
        )

    jobs = workflow.get("jobs", {})

    if not jobs:
        findings.append(
            "HIGH: Workflow does not define any jobs."
        )

    for job_name, job in jobs.items():
        findings.extend(
            audit_job(job_name, job)
        )

    findings.extend(
        find_hardcoded_secrets(workflow)
    )

    findings.extend(
        find_aws_credentials(workflow)
    )

    security_tools = has_security_scanning(
        workflow
    )

    if security_tools:
        print(
            "Security tools detected: "
            + ", ".join(security_tools)
        )
    else:
        findings.append(
            "LOW: No recognised security scanning tool "
            "was detected."
        )

    if not findings:
        print("Status: COMPLIANT")
        return 0

    for finding in findings:
        print(f"  - {finding}")

    return len(findings)


def get_workflow_files():
    files = list(
        WORKFLOW_DIRECTORY.glob("*.yaml")
    )

    files.extend(
        WORKFLOW_DIRECTORY.glob("*.yml")
    )

    return sorted(set(files))


def main():
    print("GITHUB ACTIONS WORKFLOW AUDITOR")
    print(f"Directory: {WORKFLOW_DIRECTORY}")

    if not WORKFLOW_DIRECTORY.exists():
        print(
            f"Workflow directory not found: "
            f"{WORKFLOW_DIRECTORY}"
        )
        sys.exit(1)

    workflow_files = get_workflow_files()

    if not workflow_files:
        print("No workflow YAML files found.")
        sys.exit(1)

    total_findings = 0

    for file_path in workflow_files:
        total_findings += audit_workflow(
            file_path
        )

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"Workflows scanned: {len(workflow_files)}")
    print(f"Total findings: {total_findings}")

    if total_findings == 0:
        print("Workflow audit PASSED.")
        sys.exit(0)

    print("Workflow audit FAILED.")
    sys.exit(1)


if __name__ == "__main__":
    main()