from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"
REPORT_HOURS = 24
METRIC_PERIOD = 3600

CPU_WARNING_THRESHOLD = 70
CPU_CRITICAL_THRESHOLD = 90


def get_instance_name(instance):
    for tag in instance.get("Tags", []):
        if tag.get("Key") == "Name":
            return tag.get("Value", "No Name")

    return "No Name"


def get_ec2_instances(ec2):
    paginator = ec2.get_paginator("describe_instances")
    instances = []

    filters = [
        {
            "Name": "instance-state-name",
            "Values": ["running"],
        }
    ]

    for page in paginator.paginate(Filters=filters):
        for reservation in page.get("Reservations", []):
            instances.extend(
                reservation.get("Instances", [])
            )

    return instances


def get_metric_values(
    cloudwatch,
    instance_id,
    metric_name,
    statistic,
):
    end_time = datetime.now(timezone.utc)

    start_time = end_time - timedelta(
        hours=REPORT_HOURS
    )

    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName=metric_name,
        Dimensions=[
            {
                "Name": "InstanceId",
                "Value": instance_id,
            }
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=METRIC_PERIOD,
        Statistics=[statistic],
    )

    return response.get("Datapoints", [])


def calculate_cpu_statistics(cloudwatch, instance_id):
    datapoints = get_metric_values(
        cloudwatch=cloudwatch,
        instance_id=instance_id,
        metric_name="CPUUtilization",
        statistic="Average",
    )

    if not datapoints:
        return None, None

    cpu_values = [
        datapoint["Average"]
        for datapoint in datapoints
    ]

    average_cpu = sum(cpu_values) / len(cpu_values)
    maximum_cpu = max(cpu_values)

    return average_cpu, maximum_cpu


def get_status_check_failures(
    cloudwatch,
    instance_id,
):
    datapoints = get_metric_values(
        cloudwatch=cloudwatch,
        instance_id=instance_id,
        metric_name="StatusCheckFailed",
        statistic="Maximum",
    )

    if not datapoints:
        return 0

    return max(
        datapoint["Maximum"]
        for datapoint in datapoints
    )


def determine_health(
    average_cpu,
    maximum_cpu,
    status_check_failed,
):
    if status_check_failed > 0:
        return "CRITICAL"

    if maximum_cpu is None:
        return "NO DATA"

    if maximum_cpu >= CPU_CRITICAL_THRESHOLD:
        return "CRITICAL"

    if maximum_cpu >= CPU_WARNING_THRESHOLD:
        return "WARNING"

    return "HEALTHY"


def get_active_alarms(cloudwatch):
    paginator = cloudwatch.get_paginator(
        "describe_alarms"
    )

    active_alarms = []

    for page in paginator.paginate(
        StateValue="ALARM",
        AlarmTypes=["MetricAlarm"],
    ):
        active_alarms.extend(
            page.get("MetricAlarms", [])
        )

    return active_alarms


def display_instance_report(
    cloudwatch,
    instance,
):
    instance_id = instance["InstanceId"]
    instance_name = get_instance_name(instance)

    average_cpu, maximum_cpu = (
        calculate_cpu_statistics(
            cloudwatch,
            instance_id,
        )
    )

    status_check_failed = (
        get_status_check_failures(
            cloudwatch,
            instance_id,
        )
    )

    health = determine_health(
        average_cpu,
        maximum_cpu,
        status_check_failed,
    )

    print("\n" + "-" * 75)
    print(f"Instance ID: {instance_id}")
    print(f"Name: {instance_name}")
    print(f"Type: {instance['InstanceType']}")
    print(f"State: {instance['State']['Name']}")

    if average_cpu is None:
        print("Average CPU: No data")
        print("Maximum CPU: No data")
    else:
        print(f"Average CPU: {average_cpu:.2f}%")
        print(f"Maximum CPU: {maximum_cpu:.2f}%")

    print(
        f"Status-check failures: "
        f"{status_check_failed}"
    )

    print(f"Health: {health}")

    return health


def display_active_alarms(active_alarms):
    print("\nACTIVE CLOUDWATCH ALARMS")
    print("=" * 75)

    if not active_alarms:
        print("No CloudWatch metric alarms are currently in ALARM.")
        return

    for alarm in active_alarms:
        print(
            f"Alarm: {alarm['AlarmName']} | "
            f"Metric: {alarm.get('MetricName', 'Unknown')} | "
            f"Reason: {alarm.get('StateReason', 'No reason')}"
        )

    print(
        f"Total active alarms: "
        f"{len(active_alarms)}"
    )


def generate_health_report(
    cloudwatch,
    instances,
):
    print("\nEC2 OPERATIONAL HEALTH REPORT")
    print("=" * 75)

    print(
        f"Reporting period: Last "
        f"{REPORT_HOURS} hours"
    )

    if not instances:
        print("No running EC2 instances found.")
        return

    health_counts = {
        "HEALTHY": 0,
        "WARNING": 0,
        "CRITICAL": 0,
        "NO DATA": 0,
    }

    for instance in instances:
        health = display_instance_report(
            cloudwatch,
            instance,
        )

        health_counts[health] += 1

    print("\n" + "=" * 75)
    print("HEALTH SUMMARY")
    print("-" * 75)
    print(f"Total instances: {len(instances)}")
    print(f"Healthy: {health_counts['HEALTHY']}")
    print(f"Warning: {health_counts['WARNING']}")
    print(f"Critical: {health_counts['CRITICAL']}")
    print(f"No data: {health_counts['NO DATA']}")


def main():
    ec2 = boto3.client(
        "ec2",
        region_name=REGION,
    )

    cloudwatch = boto3.client(
        "cloudwatch",
        region_name=REGION,
    )

    print(f"Region: {REGION}")

    try:
        instances = get_ec2_instances(ec2)

        generate_health_report(
            cloudwatch,
            instances,
        )

        active_alarms = get_active_alarms(
            cloudwatch
        )

        display_active_alarms(
            active_alarms
        )

    except ClientError as error:
        details = error.response.get(
            "Error",
            {}
        )

        print(
            f"AWS error: "
            f"{details.get('Code')} - "
            f"{details.get('Message')}"
        )


if __name__ == "__main__":
    main()