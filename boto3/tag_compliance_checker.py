import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

REQUIRED_TAGS = [
    "Environment",
    "Owner",
    "Project",
    "ManagedBy",
]


def convert_tags_to_dictionary(tags):
    tag_dictionary = {}

    for tag in tags:
        key = tag.get("Key")
        value = tag.get("Value", "")

        if key:
            tag_dictionary[key] = value

    return tag_dictionary


def get_resources(tagging_client):
    paginator = tagging_client.get_paginator("get_resources")

    resources = []

    for page in paginator.paginate():
        resources.extend(
            page.get("ResourceTagMappingList", [])
        )

    return resources


def find_missing_tags(resource_tags):
    missing_tags = []

    for required_tag in REQUIRED_TAGS:
        if required_tag not in resource_tags:
            missing_tags.append(required_tag)

    return missing_tags


def check_tag_compliance(resources):
    compliant_count = 0
    non_compliant_count = 0

    print("\nTAG COMPLIANCE REPORT")
    print("-" * 80)

    if not resources:
        print("No tagged or previously tagged resources found.")
        return

    for resource in resources:
        resource_arn = resource["ResourceARN"]

        tags = convert_tags_to_dictionary(
            resource.get("Tags", [])
        )

        missing_tags = find_missing_tags(tags)

        if missing_tags:
            non_compliant_count += 1

            print(f"\nNON-COMPLIANT: {resource_arn}")
            print(
                f"Missing tags: {', '.join(missing_tags)}"
            )

        else:
            compliant_count += 1
            print(f"\nCOMPLIANT: {resource_arn}")

    total_resources = (
        compliant_count + non_compliant_count
    )

    compliance_percentage = (
        compliant_count / total_resources
    ) * 100

    print("\n" + "=" * 80)
    print(f"Total resources: {total_resources}")
    print(f"Compliant resources: {compliant_count}")
    print(
        f"Non-compliant resources: "
        f"{non_compliant_count}"
    )
    print(
        f"Compliance percentage: "
        f"{compliance_percentage:.2f}%"
    )


def main():
    tagging_client = boto3.client(
        "resourcegroupstaggingapi",
        region_name=REGION,
    )

    print(f"Checking resource tags in region: {REGION}")
    print(
        f"Required tags: {', '.join(REQUIRED_TAGS)}"
    )

    try:
        resources = get_resources(tagging_client)
        check_tag_compliance(resources)

    except ClientError as error:
        details = error.response.get("Error", {})

        print(
            f"AWS error: "
            f"{details.get('Code')} - "
            f"{details.get('Message')}"
        )


if __name__ == "__main__":
    main()