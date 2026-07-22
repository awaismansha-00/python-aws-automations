from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"
EXPIRY_WARNING_DAYS = 30


def calculate_days_until_expiry(expiry_date):
    current_time = datetime.now(timezone.utc)
    return (expiry_date - current_time).days


def get_hosted_zones(route53):
    paginator = route53.get_paginator(
        "list_hosted_zones"
    )

    hosted_zones = []

    for page in paginator.paginate():
        hosted_zones.extend(
            page.get("HostedZones", [])
        )

    return hosted_zones


def get_dns_records(route53, hosted_zone_id):
    paginator = route53.get_paginator(
        "list_resource_record_sets"
    )

    records = []

    for page in paginator.paginate(
        HostedZoneId=hosted_zone_id
    ):
        records.extend(
            page.get("ResourceRecordSets", [])
        )

    return records


def get_record_value(record):
    if "AliasTarget" in record:
        return record["AliasTarget"].get(
            "DNSName",
            "Unknown alias",
        )

    resource_records = record.get(
        "ResourceRecords",
        [],
    )

    values = [
        resource.get("Value", "")
        for resource in resource_records
    ]

    return ", ".join(values) or "No value"


def audit_route53(route53):
    hosted_zones = get_hosted_zones(route53)

    print("\nROUTE 53 AUDIT")
    print("=" * 80)

    if not hosted_zones:
        print("No Route 53 hosted zones found.")
        return

    total_records = 0

    for hosted_zone in hosted_zones:
        zone_id = hosted_zone["Id"]
        zone_name = hosted_zone["Name"]
        private_zone = hosted_zone.get(
            "Config",
            {},
        ).get("PrivateZone", False)

        print("\n" + "-" * 80)
        print(f"Hosted zone: {zone_name}")
        print(f"Zone ID: {zone_id}")
        print(f"Private zone: {private_zone}")

        records = get_dns_records(
            route53,
            zone_id,
        )

        for record in records:
            total_records += 1

            print(
                f"Record: {record['Name']} | "
                f"Type: {record['Type']} | "
                f"Value: {get_record_value(record)}"
            )

        print(
            f"Records in zone: {len(records)}"
        )

    print("\n" + "=" * 80)
    print(f"Hosted zones: {len(hosted_zones)}")
    print(f"Total DNS records: {total_records}")


def get_certificates(acm):
    paginator = acm.get_paginator(
        "list_certificates"
    )

    certificates = []

    for page in paginator.paginate():
        certificates.extend(
            page.get("CertificateSummaryList", [])
        )

    return certificates


def audit_acm(acm):
    certificates = get_certificates(acm)

    print("\nACM CERTIFICATE AUDIT")
    print("=" * 80)

    if not certificates:
        print(
            f"No ACM certificates found in {REGION}."
        )
        return

    warning_count = 0
    unused_count = 0

    for certificate_summary in certificates:
        certificate_arn = certificate_summary[
            "CertificateArn"
        ]

        response = acm.describe_certificate(
            CertificateArn=certificate_arn
        )

        certificate = response["Certificate"]

        domain_name = certificate.get(
            "DomainName",
            "Unknown",
        )

        status = certificate.get(
            "Status",
            "Unknown",
        )

        expiry_date = certificate.get("NotAfter")
        resources_in_use = certificate.get(
            "InUseBy",
            [],
        )

        print("\n" + "-" * 80)
        print(f"Domain: {domain_name}")
        print(f"Status: {status}")
        print(f"Certificate ARN: {certificate_arn}")

        if expiry_date:
            days_remaining = calculate_days_until_expiry(
                expiry_date
            )

            print(f"Expiry date: {expiry_date}")
            print(
                f"Days until expiry: {days_remaining}"
            )

            if days_remaining <= EXPIRY_WARNING_DAYS:
                warning_count += 1
                print(
                    f"WARNING: Certificate expires within "
                    f"{EXPIRY_WARNING_DAYS} days."
                )
        else:
            print("Expiry date: Not available")

        if resources_in_use:
            print("Used by:")

            for resource_arn in resources_in_use:
                print(f"  - {resource_arn}")
        else:
            unused_count += 1
            print(
                "WARNING: Certificate is not attached "
                "to any AWS resource."
            )

    print("\n" + "=" * 80)
    print(f"Certificates scanned: {len(certificates)}")
    print(
        f"Certificates nearing expiry: "
        f"{warning_count}"
    )
    print(f"Unused certificates: {unused_count}")


def main():
    route53 = boto3.client("route53")

    acm = boto3.client(
        "acm",
        region_name=REGION,
    )

    print(f"ACM region: {REGION}")

    try:
        audit_route53(route53)
        audit_acm(acm)

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