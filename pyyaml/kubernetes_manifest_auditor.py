import sys
from pathlib import Path

import yaml


MANIFEST_DIRECTORY = Path("kubernetes")

REQUIRED_LABELS = [
    "app",
    "environment",
]

APPROVED_IMAGE_REGISTRIES = [
    "docker.io/",
    "ghcr.io/",
    "public.ecr.aws/",
    "123456789012.dkr.ecr.eu-west-2.amazonaws.com/",
]


def load_yaml_documents(file_path):
    with file_path.open("r", encoding="utf-8") as file:
        return list(yaml.safe_load_all(file))


def has_approved_registry(image):
    return any(
        image.startswith(registry)
        for registry in APPROVED_IMAGE_REGISTRIES
    )


def audit_container(container):
    findings = []

    container_name = container.get(
        "name",
        "Unnamed container",
    )

    image = container.get("image")

    if not image:
        findings.append(
            f"HIGH: Container '{container_name}' "
            "does not define an image."
        )
    elif not has_approved_registry(image):
        findings.append(
            f"MEDIUM: Container '{container_name}' "
            f"uses an unapproved image registry: {image}"
        )

    resources = container.get("resources", {})

    requests = resources.get("requests", {})
    limits = resources.get("limits", {})

    for resource_name in ["cpu", "memory"]:
        if resource_name not in requests:
            findings.append(
                f"MEDIUM: Container '{container_name}' "
                f"is missing {resource_name} request."
            )

        if resource_name not in limits:
            findings.append(
                f"MEDIUM: Container '{container_name}' "
                f"is missing {resource_name} limit."
            )

    if "readinessProbe" not in container:
        findings.append(
            f"MEDIUM: Container '{container_name}' "
            "is missing a readiness probe."
        )

    if "livenessProbe" not in container:
        findings.append(
            f"MEDIUM: Container '{container_name}' "
            "is missing a liveness probe."
        )

    security_context = container.get(
        "securityContext",
        {},
    )

    if security_context.get("runAsNonRoot") is not True:
        findings.append(
            f"HIGH: Container '{container_name}' "
            "does not enforce runAsNonRoot=true."
        )

    if security_context.get(
        "allowPrivilegeEscalation"
    ) is not False:
        findings.append(
            f"HIGH: Container '{container_name}' "
            "does not set allowPrivilegeEscalation=false."
        )

    return findings


def audit_deployment(document):
    findings = []

    metadata = document.get("metadata", {})
    specification = document.get("spec", {})

    deployment_name = metadata.get(
        "name",
        "Unnamed deployment",
    )

    namespace = metadata.get("namespace")

    if not namespace:
        findings.append(
            "MEDIUM: Deployment does not define a namespace."
        )

    labels = metadata.get("labels", {})

    for required_label in REQUIRED_LABELS:
        if required_label not in labels:
            findings.append(
                f"LOW: Missing required label "
                f"'{required_label}'."
            )

    replicas = specification.get("replicas")

    if replicas is None:
        findings.append(
            "LOW: Replica count is not explicitly defined."
        )
    elif replicas < 2:
        findings.append(
            "LOW: Deployment has fewer than 2 replicas."
        )

    pod_template = specification.get(
        "template",
        {},
    )

    pod_specification = pod_template.get(
        "spec",
        {},
    )

    pod_security_context = pod_specification.get(
        "securityContext",
        {},
    )

    if "runAsNonRoot" not in pod_security_context:
        findings.append(
            "LOW: Pod security context does not define "
            "runAsNonRoot."
        )

    containers = pod_specification.get(
        "containers",
        [],
    )

    if not containers:
        findings.append(
            "HIGH: Deployment does not define any containers."
        )

    for container in containers:
        findings.extend(
            audit_container(container)
        )

    return deployment_name, findings


def audit_file(file_path):
    print("\n" + "=" * 80)
    print(f"FILE: {file_path}")
    print("=" * 80)

    try:
        documents = load_yaml_documents(file_path)

    except yaml.YAMLError as error:
        print(f"HIGH: Invalid YAML syntax: {error}")
        return 1, 1

    deployment_count = 0
    finding_count = 0

    for document in documents:
        if not document:
            continue

        kind = document.get("kind")

        if kind != "Deployment":
            continue

        deployment_count += 1

        deployment_name, findings = audit_deployment(
            document
        )

        print(f"\nDeployment: {deployment_name}")

        if not findings:
            print("Status: COMPLIANT")
            continue

        for finding in findings:
            print(f"  - {finding}")

        finding_count += len(findings)

    if deployment_count == 0:
        print("No Deployment manifests found.")

    return deployment_count, finding_count


def get_yaml_files():
    yaml_files = list(
        MANIFEST_DIRECTORY.rglob("*.yaml")
    )

    yaml_files.extend(
        MANIFEST_DIRECTORY.rglob("*.yml")
    )

    return sorted(set(yaml_files))


def main():
    print("KUBERNETES MANIFEST AUDITOR")
    print(f"Directory: {MANIFEST_DIRECTORY}")

    if not MANIFEST_DIRECTORY.exists():
        print(
            f"Directory does not exist: "
            f"{MANIFEST_DIRECTORY}"
        )
        sys.exit(1)

    yaml_files = get_yaml_files()

    if not yaml_files:
        print("No YAML files found.")
        sys.exit(1)

    total_deployments = 0
    total_findings = 0

    for file_path in yaml_files:
        deployment_count, finding_count = (
            audit_file(file_path)
        )

        total_deployments += deployment_count
        total_findings += finding_count

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"Files scanned: {len(yaml_files)}")
    print(f"Deployments scanned: {total_deployments}")
    print(f"Total findings: {total_findings}")

    if total_findings == 0:
        print("Manifest audit PASSED.")
        sys.exit(0)

    print("Manifest audit FAILED.")
    sys.exit(1)


if __name__ == "__main__":
    main()