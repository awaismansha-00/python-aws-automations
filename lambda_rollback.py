import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

FUNCTION_NAME = "my-lambda-function"
ALIAS_NAME = "prod"

# Version to which the alias should be rolled back.
TARGET_VERSION = "2"

# Keep True while testing.
DRY_RUN = True


def get_current_alias(lambda_client):
    response = lambda_client.get_alias(
        FunctionName=FUNCTION_NAME,
        Name=ALIAS_NAME,
    )

    return response


def get_published_versions(lambda_client):
    paginator = lambda_client.get_paginator(
        "list_versions_by_function"
    )

    versions = []

    for page in paginator.paginate(
        FunctionName=FUNCTION_NAME
    ):
        versions.extend(
            page.get("Versions", [])
        )

    return versions


def display_versions(versions):
    print("\nPUBLISHED LAMBDA VERSIONS")
    print("-" * 70)

    published_versions = [
        version
        for version in versions
        if version["Version"] != "$LATEST"
    ]

    if not published_versions:
        print("No published versions found.")
        return

    for version in published_versions:
        print(
            f"Version: {version['Version']} | "
            f"Runtime: {version.get('Runtime', 'Unknown')} | "
            f"Last modified: "
            f"{version.get('LastModified', 'Unknown')}"
        )


def version_exists(versions, target_version):
    for version in versions:
        if version["Version"] == target_version:
            return True

    return False


def rollback_alias(lambda_client):
    alias = get_current_alias(lambda_client)

    current_version = alias["FunctionVersion"]

    print("\nLAMBDA ROLLBACK")
    print("-" * 70)
    print(f"Function: {FUNCTION_NAME}")
    print(f"Alias: {ALIAS_NAME}")
    print(f"Current version: {current_version}")
    print(f"Target version: {TARGET_VERSION}")

    if current_version == TARGET_VERSION:
        print(
            "The alias already points to the "
            "target version."
        )
        return

    versions = get_published_versions(
        lambda_client
    )

    display_versions(versions)

    if not version_exists(
        versions,
        TARGET_VERSION,
    ):
        print(
            f"\nVersion {TARGET_VERSION} does not exist."
        )
        return

    if DRY_RUN:
        print(
            f"\nDry run enabled. Alias "
            f"{ALIAS_NAME} would be changed from "
            f"version {current_version} to "
            f"version {TARGET_VERSION}."
        )
        return

    response = lambda_client.update_alias(
        FunctionName=FUNCTION_NAME,
        Name=ALIAS_NAME,
        FunctionVersion=TARGET_VERSION,
        Description=(
            f"Rolled back from version "
            f"{current_version} to "
            f"{TARGET_VERSION}"
        ),
    )

    print("\nRollback completed.")
    print(
        f"Alias {response['Name']} now points to "
        f"version {response['FunctionVersion']}."
    )


def main():
    lambda_client = boto3.client(
        "lambda",
        region_name=REGION,
    )

    print(f"Region: {REGION}")
    print(f"Dry run: {DRY_RUN}")

    try:
        rollback_alias(lambda_client)

    except ClientError as error:
        details = error.response.get(
            "Error",
            {},
        )

        print(
            f"AWS error: "
            f"{details.get('Code')} - "
            f"{details.get('Message')}"
        )


if __name__ == "__main__":
    main()