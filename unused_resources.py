from datetime import datetime, timezone

import boto3


REGION = "eu-west-2"
AGE_THRESHOLD_DAYS = 30


def calculate_age(created_time):
    current_time = datetime.now(timezone.utc)
    age = current_time - created_time

    return age.days


def find_unattached_ebs_volumes(ec2):
    paginator = ec2.get_paginator("describe_volumes")
    count = 0

    print("\nUNATTACHED EBS VOLUMES")
    print("-" * 70)

    for page in paginator.paginate(
        Filters=[
            {
                "Name": "status",
                "Values": ["available"],
            }
        ]
    ):
        for volume in page.get("Volumes", []):
            attachments = volume.get("Attachments", [])

            if not attachments:
                count += 1
                age = calculate_age(volume["CreateTime"])

                print(
                    f"Volume ID: {volume['VolumeId']} | "
                    f"Size: {volume['Size']} GiB | "
                    f"Type: {volume['VolumeType']} | "
                    f"Age: {age} days"
                )

    if count == 0:
        print("No unattached EBS volumes found.")

    print(f"Total unattached EBS volumes: {count}")


def find_unassociated_elastic_ips(ec2):
    response = ec2.describe_addresses()
    addresses = response.get("Addresses", [])

    count = 0

    print("\nUNASSOCIATED ELASTIC IPS")
    print("-" * 70)

    for address in addresses:
        association_id = address.get("AssociationId")
        network_interface_id = address.get("NetworkInterfaceId")
        instance_id = address.get("InstanceId")

        if not association_id and not network_interface_id and not instance_id:
            count += 1

            print(
                f"Public IP: {address.get('PublicIp')} | "
                f"Allocation ID: "
                f"{address.get('AllocationId', 'Not available')}"
            )

    if count == 0:
        print("No unassociated Elastic IPs found.")

    print(f"Total unassociated Elastic IPs: {count}")


def find_stopped_ec2_instances(ec2):
    paginator = ec2.get_paginator("describe_instances")
    count = 0

    print("\nSTOPPED EC2 INSTANCES")
    print("-" * 70)

    filters = [
        {
            "Name": "instance-state-name",
            "Values": ["stopped"],
        }
    ]

    for page in paginator.paginate(Filters=filters):
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                count += 1

                instance_name = "No Name"

                for tag in instance.get("Tags", []):
                    if tag.get("Key") == "Name":
                        instance_name = tag.get("Value", "No Name")

                print(
                    f"Instance ID: {instance['InstanceId']} | "
                    f"Name: {instance_name} | "
                    f"Type: {instance['InstanceType']} | "
                    f"Launch time: {instance['LaunchTime']}"
                )

    if count == 0:
        print("No stopped EC2 instances found.")

    print(f"Total stopped EC2 instances: {count}")


def find_old_snapshots(ec2):
    paginator = ec2.get_paginator("describe_snapshots")
    count = 0

    print(
        f"\nEBS SNAPSHOTS OLDER THAN {AGE_THRESHOLD_DAYS} DAYS"
    )
    print("-" * 70)

    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page.get("Snapshots", []):
            age = calculate_age(snapshot["StartTime"])

            if age >= AGE_THRESHOLD_DAYS:
                count += 1

                print(
                    f"Snapshot ID: {snapshot['SnapshotId']} | "
                    f"Volume ID: "
                    f"{snapshot.get('VolumeId', 'Unknown')} | "
                    f"Size: {snapshot['VolumeSize']} GiB | "
                    f"Age: {age} days | "
                    f"State: {snapshot['State']}"
                )

    if count == 0:
        print(
            f"No snapshots older than "
            f"{AGE_THRESHOLD_DAYS} days found."
        )

    print(f"Total old snapshots: {count}")


def main():
    print(f"Scanning unused AWS resources in region: {REGION}")

    ec2 = boto3.client("ec2", region_name=REGION)

    find_unattached_ebs_volumes(ec2)
    find_unassociated_elastic_ips(ec2)
    find_stopped_ec2_instances(ec2)
    find_old_snapshots(ec2)


if __name__ == "__main__":
    main()