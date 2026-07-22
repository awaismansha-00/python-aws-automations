import time

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

COMMANDS = [
    "echo '=== HOSTNAME ==='",
    "hostname",
    "echo '=== UPTIME ==='",
    "uptime",
    "echo '=== MEMORY ==='",
    "free -h",
    "echo '=== DISK USAGE ==='",
    "df -h",
    "echo '=== CPU LOAD ==='",
    "cat /proc/loadavg",
]


def get_managed_instances(ssm):
    paginator = ssm.get_paginator(
        "describe_instance_information"
    )

    managed_instances = []

    for page in paginator.paginate():
        managed_instances.extend(
            page.get("InstanceInformationList", [])
        )

    return managed_instances


def display_managed_instances(instances):
    print("\nSSM MANAGED INSTANCES")
    print("-" * 75)

    if not instances:
        print("No Systems Manager managed instances found.")
        return

    for instance in instances:
        print(
            f"Instance ID: {instance['InstanceId']} | "
            f"Platform: {instance.get('PlatformName', 'Unknown')} | "
            f"Status: {instance.get('PingStatus', 'Unknown')} | "
            f"SSM Agent: {instance.get('AgentVersion', 'Unknown')}"
        )

    print(f"Total managed instances: {len(instances)}")


def send_health_check_command(ssm, instance_ids):
    response = ssm.send_command(
        InstanceIds=instance_ids,
        DocumentName="AWS-RunShellScript",
        Comment="Automated server health check",
        Parameters={
            "commands": COMMANDS
        },
        TimeoutSeconds=60,
    )

    return response["Command"]["CommandId"]


def wait_for_command(ssm, command_id, instance_id):
    pending_statuses = [
        "Pending",
        "InProgress",
        "Delayed",
    ]

    while True:
        try:
            response = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id,
            )

            status = response["Status"]

            if status not in pending_statuses:
                return response

        except ssm.exceptions.InvocationDoesNotExist:
            # Run Command uses eventual consistency, so the
            # invocation may not be available immediately.
            pass

        time.sleep(2)


def display_command_result(instance_id, result):
    print("\n" + "=" * 75)
    print(f"INSTANCE: {instance_id}")
    print(f"STATUS: {result['Status']}")
    print("=" * 75)

    standard_output = result.get(
        "StandardOutputContent",
        "",
    )

    standard_error = result.get(
        "StandardErrorContent",
        "",
    )

    if standard_output:
        print("\nOUTPUT")
        print("-" * 75)
        print(standard_output)

    if standard_error:
        print("\nERROR OUTPUT")
        print("-" * 75)
        print(standard_error)


def run_health_check(ssm, instances):
    online_instances = [
        instance
        for instance in instances
        if instance.get("PingStatus") == "Online"
        and instance.get("PlatformType") == "Linux"
    ]

    if not online_instances:
        print(
            "\nNo online Linux managed instances found."
        )
        return

    instance_ids = [
        instance["InstanceId"]
        for instance in online_instances
    ]

    print(
        f"\nSending health-check command to "
        f"{len(instance_ids)} instance(s)..."
    )

    command_id = send_health_check_command(
        ssm,
        instance_ids,
    )

    print(f"Command ID: {command_id}")

    for instance_id in instance_ids:
        result = wait_for_command(
            ssm,
            command_id,
            instance_id,
        )

        display_command_result(
            instance_id,
            result,
        )


def main():
    ssm = boto3.client(
        "ssm",
        region_name=REGION,
    )

    print(f"Region: {REGION}")

    try:
        instances = get_managed_instances(ssm)

        display_managed_instances(instances)

        run_health_check(
            ssm,
            instances,
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