import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

# Choose "start" or "stop"
ACTION = "stop"

# Keep True while testing.
# Change to False when you want to perform the action.
DRY_RUN = True

TAG_KEY = "AutoSchedule"
TAG_VALUE = "true"


def get_instance_name(instance):
    for tag in instance.get("Tags", []):
        if tag.get("Key") == "Name":
            return tag.get("Value", "No Name")

    return "No Name"


def get_scheduled_instances(ec2, required_state):
    paginator = ec2.get_paginator("describe_instances")

    filters = [
        {
            "Name": f"tag:{TAG_KEY}",
            "Values": [TAG_VALUE],
        },
        {
            "Name": "instance-state-name",
            "Values": [required_state],
        },
    ]

    instances = []

    for page in paginator.paginate(Filters=filters):
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instances.append(instance)

    return instances


def display_instances(instances):
    if not instances:
        print("No matching EC2 instances found.")
        return

    for instance in instances:
        print(
            f"Instance ID: {instance['InstanceId']} | "
            f"Name: {get_instance_name(instance)} | "
            f"State: {instance['State']['Name']} | "
            f"Type: {instance['InstanceType']}"
        )


def start_instances(ec2):
    instances = get_scheduled_instances(
        ec2=ec2,
        required_state="stopped",
    )

    print("\nEC2 INSTANCES TO START")
    print("-" * 70)

    display_instances(instances)

    instance_ids = [
        instance["InstanceId"]
        for instance in instances
    ]

    if not instance_ids:
        return

    if DRY_RUN:
        print("\nDry run enabled. No instances were started.")
        return

    response = ec2.start_instances(
        InstanceIds=instance_ids
    )

    for change in response.get("StartingInstances", []):
        print(
            f"Starting: {change['InstanceId']} | "
            f"Previous state: "
            f"{change['PreviousState']['Name']} | "
            f"Current state: "
            f"{change['CurrentState']['Name']}"
        )


def stop_instances(ec2):
    instances = get_scheduled_instances(
        ec2=ec2,
        required_state="running",
    )

    print("\nEC2 INSTANCES TO STOP")
    print("-" * 70)

    display_instances(instances)

    instance_ids = [
        instance["InstanceId"]
        for instance in instances
    ]

    if not instance_ids:
        return

    if DRY_RUN:
        print("\nDry run enabled. No instances were stopped.")
        return

    response = ec2.stop_instances(
        InstanceIds=instance_ids
    )

    for change in response.get("StoppingInstances", []):
        print(
            f"Stopping: {change['InstanceId']} | "
            f"Previous state: "
            f"{change['PreviousState']['Name']} | "
            f"Current state: "
            f"{change['CurrentState']['Name']}"
        )


def main():
    ec2 = boto3.client(
        "ec2",
        region_name=REGION,
    )

    print(f"Region: {REGION}")
    print(f"Action: {ACTION}")
    print(f"Dry run: {DRY_RUN}")
    print(f"Required tag: {TAG_KEY}={TAG_VALUE}")

    try:
        if ACTION == "start":
            start_instances(ec2)

        elif ACTION == "stop":
            stop_instances(ec2)

        else:
            print(
                "Invalid ACTION. Use either "
                "'start' or 'stop'."
            )

    except ClientError as error:
        error_details = error.response.get("Error", {})

        print(
            f"AWS error: "
            f"{error_details.get('Code')} - "
            f"{error_details.get('Message')}"
        )


if __name__ == "__main__":
    main()