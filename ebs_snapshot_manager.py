from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

BACKUP_TAG_KEY = "Backup"
BACKUP_TAG_VALUE = "true"

RETENTION_DAYS = 30

# Change this to:
# "create" -> create snapshots
# "list"   -> list owned snapshots
# "audit"  -> find old snapshots
ACTION = "create"


def calculate_age(created_time):
    current_time = datetime.now(timezone.utc)
    return (current_time - created_time).days


def get_volume_name(volume):
    for tag in volume.get("Tags", []):
        if tag.get("Key") == "Name":
            return tag.get("Value", "No Name")

    return "No Name"


def get_backup_volumes(ec2):
    paginator = ec2.get_paginator("describe_volumes")

    filters = [
        {
            "Name": f"tag:{BACKUP_TAG_KEY}",
            "Values": [BACKUP_TAG_VALUE],
        }
    ]

    volumes = []

    for page in paginator.paginate(Filters=filters):
        volumes.extend(page.get("Volumes", []))

    return volumes


def create_snapshots(ec2):
    volumes = get_backup_volumes(ec2)

    print("\nVOLUMES SELECTED FOR BACKUP")
    print("-" * 70)

    if not volumes:
        print(
            f"No EBS volumes found with "
            f"{BACKUP_TAG_KEY}={BACKUP_TAG_VALUE}"
        )
        return

    for volume in volumes:
        volume_id = volume["VolumeId"]
        volume_name = get_volume_name(volume)

        print(
            f"Creating snapshot for: {volume_id} | "
            f"Name: {volume_name} | "
            f"Size: {volume['Size']} GiB"
        )

        description = (
            f"Automated backup of {volume_id} "
            f"created on {datetime.now(timezone.utc).date()}"
        )

        response = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=description,
            TagSpecifications=[
                {
                    "ResourceType": "snapshot",
                    "Tags": [
                        {
                            "Key": "Name",
                            "Value": f"{volume_name}-backup",
                        },
                        {
                            "Key": "SourceVolume",
                            "Value": volume_id,
                        },
                        {
                            "Key": "CreatedBy",
                            "Value": "Boto3SnapshotManager",
                        },
                        {
                            "Key": "RetentionDays",
                            "Value": str(RETENTION_DAYS),
                        },
                    ],
                }
            ],
        )

        print(
            f"Snapshot created: {response['SnapshotId']} | "
            f"State: {response['State']}"
        )


def list_snapshots(ec2):
    paginator = ec2.get_paginator("describe_snapshots")
    count = 0

    print("\nEBS SNAPSHOTS")
    print("-" * 70)

    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page.get("Snapshots", []):
            count += 1
            age = calculate_age(snapshot["StartTime"])

            print(
                f"Snapshot ID: {snapshot['SnapshotId']} | "
                f"Volume ID: {snapshot.get('VolumeId', 'Unknown')} | "
                f"Size: {snapshot['VolumeSize']} GiB | "
                f"State: {snapshot['State']} | "
                f"Age: {age} days"
            )

    if count == 0:
        print("No EBS snapshots found.")

    print(f"Total snapshots: {count}")


def audit_old_snapshots(ec2):
    paginator = ec2.get_paginator("describe_snapshots")
    count = 0

    print(
        f"\nSNAPSHOTS OLDER THAN {RETENTION_DAYS} DAYS"
    )
    print("-" * 70)

    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page.get("Snapshots", []):
            age = calculate_age(snapshot["StartTime"])

            if age >= RETENTION_DAYS:
                count += 1

                print(
                    f"Snapshot ID: {snapshot['SnapshotId']} | "
                    f"Volume ID: "
                    f"{snapshot.get('VolumeId', 'Unknown')} | "
                    f"Size: {snapshot['VolumeSize']} GiB | "
                    f"Age: {age} days"
                )

    if count == 0:
        print(
            f"No snapshots older than "
            f"{RETENTION_DAYS} days found."
        )

    print(f"Total old snapshots: {count}")


def main():
    ec2 = boto3.client(
        "ec2",
        region_name=REGION,
    )

    print(f"Region: {REGION}")
    print(f"Action: {ACTION}")

    try:
        if ACTION == "create":
            create_snapshots(ec2)

        elif ACTION == "list":
            list_snapshots(ec2)

        elif ACTION == "audit":
            audit_old_snapshots(ec2)

        else:
            print(
                "Invalid ACTION. Use "
                "'create', 'list', or 'audit'."
            )

    except ClientError as error:
        details = error.response.get("Error", {})

        print(
            f"AWS error: "
            f"{details.get('Code')} - "
            f"{details.get('Message')}"
        )


if __name__ == "__main__":
    main()