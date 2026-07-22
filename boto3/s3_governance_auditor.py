import boto3
from botocore.exceptions import ClientError


def get_buckets(s3):
    response = s3.list_buckets()
    return response.get("Buckets", [])


def get_bucket_region(s3, bucket_name):
    response = s3.get_bucket_location(
        Bucket=bucket_name
    )

    region = response.get("LocationConstraint")

    # AWS returns None for us-east-1.
    if region is None:
        return "us-east-1"

    # Older EU value represents eu-west-1.
    if region == "EU":
        return "eu-west-1"

    return region


def check_public_access(s3, bucket_name):
    try:
        response = s3.get_public_access_block(
            Bucket=bucket_name
        )

        configuration = response[
            "PublicAccessBlockConfiguration"
        ]

        settings = [
            configuration.get("BlockPublicAcls", False),
            configuration.get("IgnorePublicAcls", False),
            configuration.get("BlockPublicPolicy", False),
            configuration.get("RestrictPublicBuckets", False),
        ]

        return all(settings)

    except ClientError as error:
        error_code = error.response["Error"]["Code"]

        if error_code == "NoSuchPublicAccessBlockConfiguration":
            return False

        raise


def check_encryption(s3, bucket_name):
    try:
        response = s3.get_bucket_encryption(
            Bucket=bucket_name
        )

        rules = response.get(
            "ServerSideEncryptionConfiguration",
            {},
        ).get("Rules", [])

        if not rules:
            return False, "Not configured"

        encryption = rules[0].get(
            "ApplyServerSideEncryptionByDefault",
            {},
        )

        algorithm = encryption.get(
            "SSEAlgorithm",
            "Unknown",
        )

        return True, algorithm

    except ClientError as error:
        error_code = error.response["Error"]["Code"]

        if error_code in [
            "ServerSideEncryptionConfigurationNotFoundError",
            "NoSuchConfiguration",
        ]:
            return False, "Not configured"

        raise


def check_versioning(s3, bucket_name):
    response = s3.get_bucket_versioning(
        Bucket=bucket_name
    )

    return response.get("Status", "Disabled")


def check_logging(s3, bucket_name):
    response = s3.get_bucket_logging(
        Bucket=bucket_name
    )

    logging_configuration = response.get(
        "LoggingEnabled"
    )

    return logging_configuration is not None


def check_lifecycle(s3, bucket_name):
    try:
        response = s3.get_bucket_lifecycle_configuration(
            Bucket=bucket_name
        )

        rules = response.get("Rules", [])

        return len(rules) > 0, len(rules)

    except ClientError as error:
        error_code = error.response["Error"]["Code"]

        if error_code in [
            "NoSuchLifecycleConfiguration",
            "NoSuchConfiguration",
        ]:
            return False, 0

        raise


def audit_bucket(s3, bucket):
    bucket_name = bucket["Name"]
    findings = []

    print("\n" + "-" * 75)
    print(f"Bucket: {bucket_name}")
    print(
        f"Created: "
        f"{bucket.get('CreationDate', 'Unknown')}"
    )

    region = get_bucket_region(
        s3,
        bucket_name,
    )

    print(f"Region: {region}")

    public_access_blocked = check_public_access(
        s3,
        bucket_name,
    )

    encryption_enabled, encryption_type = (
        check_encryption(
            s3,
            bucket_name,
        )
    )

    versioning_status = check_versioning(
        s3,
        bucket_name,
    )

    logging_enabled = check_logging(
        s3,
        bucket_name,
    )

    lifecycle_enabled, lifecycle_rule_count = (
        check_lifecycle(
            s3,
            bucket_name,
        )
    )

    print(
        f"Block Public Access: "
        f"{public_access_blocked}"
    )

    print(
        f"Default encryption: "
        f"{encryption_enabled} "
        f"({encryption_type})"
    )

    print(f"Versioning: {versioning_status}")
    print(f"Access logging: {logging_enabled}")

    print(
        f"Lifecycle rules: "
        f"{lifecycle_rule_count}"
    )

    if not public_access_blocked:
        findings.append(
            "HIGH: All four bucket-level "
            "Block Public Access settings are not enabled"
        )

    if not encryption_enabled:
        findings.append(
            "MEDIUM: Default bucket encryption "
            "is not explicitly configured"
        )

    if versioning_status != "Enabled":
        findings.append(
            "MEDIUM: Bucket versioning is not enabled"
        )

    if not logging_enabled:
        findings.append(
            "LOW: Server access logging is not enabled"
        )

    if not lifecycle_enabled:
        findings.append(
            "LOW: No lifecycle rules are configured"
        )

    if findings:
        print("Findings:")

        for finding in findings:
            print(f"  - {finding}")
    else:
        print("Governance status: COMPLIANT")

    return len(findings)


def main():
    s3 = boto3.client("s3")

    print("\nS3 GOVERNANCE AUDIT")
    print("=" * 75)

    try:
        buckets = get_buckets(s3)

        if not buckets:
            print("No S3 buckets found.")
            return

        total_findings = 0
        buckets_with_findings = 0

        for bucket in buckets:
            finding_count = audit_bucket(
                s3,
                bucket,
            )

            total_findings += finding_count

            if finding_count > 0:
                buckets_with_findings += 1

        print("\n" + "=" * 75)
        print("S3 AUDIT SUMMARY")
        print("=" * 75)
        print(f"Buckets scanned: {len(buckets)}")
        print(
            f"Buckets with findings: "
            f"{buckets_with_findings}"
        )
        print(
            f"Total findings: "
            f"{total_findings}"
        )

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