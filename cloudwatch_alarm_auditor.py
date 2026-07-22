import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

REQUIRED_EC2_ALARMS = [
    "CPUUtilization",
    "StatusCheckFailed",
]


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
            "Values": ["running", "stopped"],
        }
    ]

    for page in paginator.paginate(Filters=filters):
        for reservation in page.get("Reservations", []):
            instances.extend(
                reservation.get("Instances", [])
            )

    return instances


def get_cloudwatch_alarms(cloudwatch):
    paginator = cloudwatch.get_paginator(
        "describe_alarms"
    )

    alarms = []

    for page in paginator.paginate(
        AlarmTypes=["MetricAlarm"]
    ):
        alarms.extend(
            page.get("MetricAlarms", [])
        )

    return alarms


def get_alarm_instance_id(alarm):
    for dimension in alarm.get("Dimensions", []):
        if dimension.get("Name") == "InstanceId":
            return dimension.get("Value")

    return None


def organise_alarms_by_instance(alarms):
    alarms_by_instance = {}

    for alarm in alarms:
        instance_id = get_alarm_instance_id(alarm)

        if not instance_id:
            continue

        if instance_id not in alarms_by_instance:
            alarms_by_instance[instance_id] = []

        alarms_by_instance[instance_id].append(alarm)

    return alarms_by_instance


def find_missing_alarms(instance_id, alarms_by_instance):
    instance_alarms = alarms_by_instance.get(
        instance_id,
        [],
    )

    existing_metrics = {
        alarm.get("MetricName")
        for alarm in instance_alarms
    }

    missing_alarms = []

    for required_metric in REQUIRED_EC2_ALARMS:
        if required_metric not in existing_metrics:
            missing_alarms.append(required_metric)

    return missing_alarms


def display_existing_alarms(instance_id, alarms_by_instance):
    instance_alarms = alarms_by_instance.get(
        instance_id,
        [],
    )

    if not instance_alarms:
        print("Existing alarms: None")
        return

    print("Existing alarms:")

    for alarm in instance_alarms:
        print(
            f"  - {alarm['AlarmName']} | "
            f"Metric: {alarm.get('MetricName')} | "
            f"State: {alarm.get('StateValue')} | "
            f"Actions enabled: "
            f"{alarm.get('ActionsEnabled')}"
        )


def audit_ec2_alarms(instances, alarms):
    alarms_by_instance = organise_alarms_by_instance(
        alarms
    )

    compliant_count = 0
    non_compliant_count = 0

    print("\nCLOUDWATCH EC2 ALARM AUDIT")
    print("=" * 75)

    if not instances:
        print("No EC2 instances found.")
        return

    for instance in instances:
        instance_id = instance["InstanceId"]
        instance_name = get_instance_name(instance)
        instance_state = instance["State"]["Name"]

        missing_alarms = find_missing_alarms(
            instance_id,
            alarms_by_instance,
        )

        print("\n" + "-" * 75)
        print(f"Instance ID: {instance_id}")
        print(f"Name: {instance_name}")
        print(f"State: {instance_state}")

        display_existing_alarms(
            instance_id,
            alarms_by_instance,
        )

        if missing_alarms:
            non_compliant_count += 1

            print(
                "Missing alarms: "
                + ", ".join(missing_alarms)
            )
        else:
            compliant_count += 1
            print("Alarm status: COMPLIANT")

    total_instances = len(instances)

    compliance_percentage = (
        compliant_count / total_instances
    ) * 100

    print("\n" + "=" * 75)
    print(f"Total EC2 instances: {total_instances}")
    print(f"Compliant instances: {compliant_count}")
    print(
        f"Non-compliant instances: "
        f"{non_compliant_count}"
    )
    print(
        f"Compliance percentage: "
        f"{compliance_percentage:.2f}%"
    )


def main():
    ec2 = boto3.client(
        "ec2",
        region_name=REGION,
    )

    cloudwatch = boto3.client(
        "cloudwatch",
        region_name=REGION,
    )

    print(
        f"Auditing CloudWatch alarms in region: "
        f"{REGION}"
    )

    try:
        instances = get_ec2_instances(ec2)
        alarms = get_cloudwatch_alarms(cloudwatch)

        audit_ec2_alarms(
            instances,
            alarms,
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