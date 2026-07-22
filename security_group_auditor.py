import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

SENSITIVE_PORTS = {
    22: "SSH",
    3389: "RDP",
    3306: "MySQL",
    5432: "PostgreSQL",
    6379: "Redis",
    9200: "Elasticsearch",
}


def get_port_range(permission):
    protocol = permission.get("IpProtocol")

    if protocol == "-1":
        return "All ports"

    from_port = permission.get("FromPort")
    to_port = permission.get("ToPort")

    if from_port is None or to_port is None:
        return "Not applicable"

    if from_port == to_port:
        return str(from_port)

    return f"{from_port}-{to_port}"


def get_risk_level(permission):
    protocol = permission.get("IpProtocol")
    from_port = permission.get("FromPort")
    to_port = permission.get("ToPort")

    if protocol == "-1":
        return "CRITICAL", "All protocols and ports are publicly accessible"

    for port, service_name in SENSITIVE_PORTS.items():
        if (
            from_port is not None
            and to_port is not None
            and from_port <= port <= to_port
        ):
            return (
                "HIGH",
                f"{service_name} port {port} is publicly accessible",
            )

    return "MEDIUM", "Public inbound access is allowed"


def audit_public_rule(
    security_group,
    permission,
    cidr,
    ip_version,
):
    severity, reason = get_risk_level(permission)

    print(f"\nSeverity: {severity}")
    print(f"Security Group: {security_group['GroupName']}")
    print(f"Group ID: {security_group['GroupId']}")
    print(f"VPC ID: {security_group.get('VpcId', 'No VPC')}")
    print(f"Protocol: {permission.get('IpProtocol')}")
    print(f"Port: {get_port_range(permission)}")
    print(f"Source: {cidr} ({ip_version})")
    print(f"Reason: {reason}")


def audit_security_groups(ec2):
    paginator = ec2.get_paginator(
        "describe_security_groups"
    )

    security_group_count = 0
    finding_count = 0

    print("\nSECURITY GROUP AUDIT")
    print("-" * 75)

    for page in paginator.paginate():
        for security_group in page.get(
            "SecurityGroups", []
        ):
            security_group_count += 1

            for permission in security_group.get(
                "IpPermissions", []
            ):
                for ip_range in permission.get(
                    "IpRanges", []
                ):
                    cidr = ip_range.get("CidrIp")

                    if cidr == "0.0.0.0/0":
                        finding_count += 1

                        audit_public_rule(
                            security_group,
                            permission,
                            cidr,
                            "IPv4",
                        )

                for ipv6_range in permission.get(
                    "Ipv6Ranges", []
                ):
                    cidr = ipv6_range.get("CidrIpv6")

                    if cidr == "::/0":
                        finding_count += 1

                        audit_public_rule(
                            security_group,
                            permission,
                            cidr,
                            "IPv6",
                        )

    print("\n" + "=" * 75)
    print(
        f"Security groups scanned: "
        f"{security_group_count}"
    )
    print(f"Public rules found: {finding_count}")

    if finding_count == 0:
        print(
            "No publicly accessible inbound "
            "security-group rules found."
        )


def main():
    ec2 = boto3.client(
        "ec2",
        region_name=REGION,
    )

    print(
        f"Scanning security groups in region: "
        f"{REGION}"
    )

    try:
        audit_security_groups(ec2)

    except ClientError as error:
        details = error.response.get("Error", {})

        print(
            f"AWS error: "
            f"{details.get('Code')} - "
            f"{details.get('Message')}"
        )


if __name__ == "__main__":
    main()