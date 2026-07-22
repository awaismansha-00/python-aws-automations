from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


ACCESS_KEY_MAX_AGE_DAYS = 90


def calculate_age(created_time):
    current_time = datetime.now(timezone.utc)
    return (current_time - created_time).days


def get_all_users(iam):
    paginator = iam.get_paginator("list_users")
    users = []

    for page in paginator.paginate():
        users.extend(page.get("Users", []))

    return users


def has_console_access(iam, username):
    try:
        iam.get_login_profile(UserName=username)
        return True

    except iam.exceptions.NoSuchEntityException:
        return False


def get_mfa_devices(iam, username):
    response = iam.list_mfa_devices(
        UserName=username
    )

    return response.get("MFADevices", [])


def get_attached_policies(iam, username):
    paginator = iam.get_paginator(
        "list_attached_user_policies"
    )

    policies = []

    for page in paginator.paginate(
        UserName=username
    ):
        policies.extend(
            page.get("AttachedPolicies", [])
        )

    return policies


def get_access_keys(iam, username):
    response = iam.list_access_keys(
        UserName=username
    )

    return response.get("AccessKeyMetadata", [])


def get_access_key_last_used(iam, access_key_id):
    response = iam.get_access_key_last_used(
        AccessKeyId=access_key_id
    )

    return response.get(
        "AccessKeyLastUsed",
        {}
    ).get("LastUsedDate")


def audit_user(iam, user):
    username = user["UserName"]
    findings = []

    console_access = has_console_access(
        iam,
        username,
    )

    mfa_devices = get_mfa_devices(
        iam,
        username,
    )

    if console_access and not mfa_devices:
        findings.append(
            "HIGH: Console access is enabled but MFA is not configured"
        )

    attached_policies = get_attached_policies(
        iam,
        username,
    )

    if attached_policies:
        policy_names = [
            policy["PolicyName"]
            for policy in attached_policies
        ]

        findings.append(
            "MEDIUM: Policies are attached directly to the user: "
            + ", ".join(policy_names)
        )

    access_keys = get_access_keys(
        iam,
        username,
    )

    for key in access_keys:
        access_key_id = key["AccessKeyId"]
        key_status = key["Status"]
        key_age = calculate_age(
            key["CreateDate"]
        )

        if key_status == "Active" and key_age > ACCESS_KEY_MAX_AGE_DAYS:
            findings.append(
                f"HIGH: Access key {access_key_id} "
                f"is {key_age} days old"
            )

        last_used = get_access_key_last_used(
            iam,
            access_key_id,
        )

        if last_used is None:
            findings.append(
                f"MEDIUM: Access key {access_key_id} "
                "has never been used"
            )
        else:
            days_since_last_use = calculate_age(
                last_used
            )

            if days_since_last_use > ACCESS_KEY_MAX_AGE_DAYS:
                findings.append(
                    f"MEDIUM: Access key {access_key_id} "
                    f"has not been used for "
                    f"{days_since_last_use} days"
                )

    print("\n" + "-" * 75)
    print(f"User: {username}")
    print(f"Created: {user['CreateDate']}")
    print(f"Console access: {console_access}")
    print(f"MFA configured: {bool(mfa_devices)}")
    print(f"Access keys: {len(access_keys)}")

    if findings:
        for finding in findings:
            print(f"Finding: {finding}")
    else:
        print("No findings.")


def audit_iam_users(iam):
    users = get_all_users(iam)

    print("\nIAM USER SECURITY AUDIT")
    print("=" * 75)

    if not users:
        print("No IAM users found.")
        return

    users_with_findings = 0

    for user in users:
        username = user["UserName"]

        console_access = has_console_access(
            iam,
            username,
        )

        mfa_devices = get_mfa_devices(
            iam,
            username,
        )

        access_keys = get_access_keys(
            iam,
            username,
        )

        has_findings = (
            (console_access and not mfa_devices)
            or bool(
                get_attached_policies(
                    iam,
                    username,
                )
            )
        )

        for key in access_keys:
            key_age = calculate_age(
                key["CreateDate"]
            )

            last_used = get_access_key_last_used(
                iam,
                key["AccessKeyId"],
            )

            if (
                key_age > ACCESS_KEY_MAX_AGE_DAYS
                or last_used is None
            ):
                has_findings = True

        if has_findings:
            users_with_findings += 1

        audit_user(iam, user)

    print("\n" + "=" * 75)
    print(f"Total IAM users: {len(users)}")
    print(
        f"Users with possible findings: "
        f"{users_with_findings}"
    )


def main():
    iam = boto3.client("iam")

    try:
        audit_iam_users(iam)

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