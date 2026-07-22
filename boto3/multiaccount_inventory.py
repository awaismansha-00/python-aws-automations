import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"
ROLE_NAME = "OrganizationAccountAccessRole"


def get_organization_accounts(organizations):
    paginator = organizations.get_paginator("list_accounts")

    accounts = []

    for page in paginator.paginate():
        accounts.extend(page.get("Accounts", []))

    return accounts


def assume_account_role(sts, account_id):
    role_arn = (
        f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    )

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="MultiAccountInventory",
    )

    return response["Credentials"]


def create_ec2_client(credentials):
    return boto3.client(
        "ec2",
        region_name=REGION,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )


def get_ec2_instances(ec2):
    paginator = ec2.get_paginator("describe_instances")

    instances = []

    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            instances.extend(
                reservation.get("Instances", [])
            )

    return instances


def get_instance_name(instance):
    for tag in instance.get("Tags", []):
        if tag.get("Key") == "Name":
            return tag.get("Value", "No Name")

    return "No Name"


def display_account_instances(account, instances):
    print("\n" + "=" * 75)
    print(f"Account: {account['Name']}")
    print(f"Account ID: {account['Id']}")
    print("=" * 75)

    if not instances:
        print("No EC2 instances found.")
        return

    for instance in instances:
        print(
            f"Instance ID: {instance['InstanceId']} | "
            f"Name: {get_instance_name(instance)} | "
            f"State: {instance['State']['Name']} | "
            f"Type: {instance['InstanceType']}"
        )

    print(f"Total instances: {len(instances)}")


def main():
    organizations = boto3.client(
        "organizations",
        region_name="us-east-1",
    )

    sts = boto3.client("sts")

    try:
        accounts = get_organization_accounts(
            organizations
        )

        print(
            f"Accounts found in organization: "
            f"{len(accounts)}"
        )

        total_instances = 0
        scanned_accounts = 0

        for account in accounts:
            account_state = account.get(
                "State",
                account.get("Status"),
            )

            if account_state != "ACTIVE":
                print(
                    f"\nSkipping account "
                    f"{account['Name']} because its "
                    f"state is {account_state}."
                )
                continue

            try:
                credentials = assume_account_role(
                    sts,
                    account["Id"],
                )

                ec2 = create_ec2_client(
                    credentials
                )

                instances = get_ec2_instances(
                    ec2
                )

                display_account_instances(
                    account,
                    instances,
                )

                scanned_accounts += 1
                total_instances += len(instances)

            except ClientError as error:
                details = error.response.get(
                    "Error",
                    {},
                )

                print(
                    f"\nCould not scan account "
                    f"{account['Name']} "
                    f"({account['Id']}): "
                    f"{details.get('Code')} - "
                    f"{details.get('Message')}"
                )

        print("\n" + "=" * 75)
        print("MULTI-ACCOUNT INVENTORY SUMMARY")
        print("=" * 75)
        print(f"Accounts scanned: {scanned_accounts}")
        print(f"Total EC2 instances: {total_instances}")

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