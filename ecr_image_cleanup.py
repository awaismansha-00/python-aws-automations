from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-2"

UNTAGGED_MAX_AGE_DAYS = 14
TAGGED_MAX_AGE_DAYS = 90
KEEP_LATEST_IMAGES = 5

PROTECTED_TAGS = {
    "latest",
    "prod",
    "production",
    "stable",
}

# Keep this True while testing.
# Change it to False only after reviewing the candidates.
DRY_RUN = True


def calculate_age(created_time):
    current_time = datetime.now(timezone.utc)
    return (current_time - created_time).days


def bytes_to_mb(size_bytes):
    return size_bytes / (1024 * 1024)


def get_repositories(ecr):
    paginator = ecr.get_paginator(
        "describe_repositories"
    )

    repositories = []

    for page in paginator.paginate():
        repositories.extend(
            page.get("repositories", [])
        )

    return repositories


def get_repository_images(ecr, repository_name):
    paginator = ecr.get_paginator(
        "describe_images"
    )

    images = []

    for page in paginator.paginate(
        repositoryName=repository_name
    ):
        images.extend(
            page.get("imageDetails", [])
        )

    return images


def is_protected_image(image):
    image_tags = image.get("imageTags", [])

    for tag in image_tags:
        if tag.lower() in PROTECTED_TAGS:
            return True

    return False


def find_cleanup_candidates(images):
    candidates = []

    # Newest images appear first.
    sorted_images = sorted(
        images,
        key=lambda image: image.get(
            "imagePushedAt",
            datetime.min.replace(
                tzinfo=timezone.utc
            ),
        ),
        reverse=True,
    )

    for index, image in enumerate(sorted_images):
        image_tags = image.get("imageTags", [])
        pushed_at = image.get("imagePushedAt")

        if not pushed_at:
            continue

        image_age = calculate_age(pushed_at)

        # Untagged image
        if not image_tags:
            if image_age >= UNTAGGED_MAX_AGE_DAYS:
                candidates.append(
                    {
                        "image": image,
                        "reason": (
                            f"Untagged image is "
                            f"{image_age} days old"
                        ),
                    }
                )

            continue

        # Never remove protected images.
        if is_protected_image(image):
            continue

        # Keep the newest configured number of images.
        if index < KEEP_LATEST_IMAGES:
            continue

        if image_age >= TAGGED_MAX_AGE_DAYS:
            candidates.append(
                {
                    "image": image,
                    "reason": (
                        f"Tagged image is "
                        f"{image_age} days old"
                    ),
                }
            )

    return candidates


def display_candidate(repository_name, candidate):
    image = candidate["image"]

    image_digest = image["imageDigest"]
    image_tags = image.get(
        "imageTags",
        ["UNTAGGED"],
    )

    image_age = calculate_age(
        image["imagePushedAt"]
    )

    image_size = bytes_to_mb(
        image.get("imageSizeInBytes", 0)
    )

    print(
        f"Repository: {repository_name} | "
        f"Digest: {image_digest[:20]}... | "
        f"Tags: {', '.join(image_tags)} | "
        f"Age: {image_age} days | "
        f"Size: {image_size:.2f} MB"
    )

    print(f"Reason: {candidate['reason']}")
    print("-" * 80)


def delete_candidates(
    ecr,
    repository_name,
    candidates,
):
    image_ids = []

    for candidate in candidates:
        image = candidate["image"]

        image_ids.append(
            {
                "imageDigest": image["imageDigest"]
            }
        )

    # ECR batch deletion accepts batches,
    # so process candidates in smaller groups.
    for start in range(0, len(image_ids), 100):
        batch = image_ids[start:start + 100]

        response = ecr.batch_delete_image(
            repositoryName=repository_name,
            imageIds=batch,
        )

        for deleted_image in response.get(
            "imageIds",
            [],
        ):
            print(
                f"Deleted: "
                f"{deleted_image.get('imageDigest')}"
            )

        for failure in response.get(
            "failures",
            [],
        ):
            print(
                f"Deletion failed: "
                f"{failure.get('failureCode')} - "
                f"{failure.get('failureReason')}"
            )


def audit_repository(ecr, repository):
    repository_name = repository[
        "repositoryName"
    ]

    print("\n" + "=" * 80)
    print(f"REPOSITORY: {repository_name}")
    print("=" * 80)

    images = get_repository_images(
        ecr,
        repository_name,
    )

    if not images:
        print("No images found.")
        return 0, 0

    candidates = find_cleanup_candidates(
        images
    )

    if not candidates:
        print("No cleanup candidates found.")
        return 0, 0

    total_size = 0

    for candidate in candidates:
        image = candidate["image"]

        total_size += image.get(
            "imageSizeInBytes",
            0,
        )

        display_candidate(
            repository_name,
            candidate,
        )

    print(
        f"Cleanup candidates: "
        f"{len(candidates)}"
    )

    print(
        f"Potential storage cleanup: "
        f"{bytes_to_mb(total_size):.2f} MB"
    )

    if DRY_RUN:
        print(
            "Dry run enabled. "
            "No images were deleted."
        )
    else:
        delete_candidates(
            ecr,
            repository_name,
            candidates,
        )

    return len(candidates), total_size


def main():
    ecr = boto3.client(
        "ecr",
        region_name=REGION,
    )

    print(f"Region: {REGION}")
    print(f"Dry run: {DRY_RUN}")
    print(
        f"Untagged retention: "
        f"{UNTAGGED_MAX_AGE_DAYS} days"
    )
    print(
        f"Tagged retention: "
        f"{TAGGED_MAX_AGE_DAYS} days"
    )
    print(
        f"Newest images retained: "
        f"{KEEP_LATEST_IMAGES}"
    )

    try:
        repositories = get_repositories(ecr)

        if not repositories:
            print("No ECR repositories found.")
            return

        total_candidates = 0
        total_size = 0

        for repository in repositories:
            candidate_count, candidate_size = (
                audit_repository(
                    ecr,
                    repository,
                )
            )

            total_candidates += candidate_count
            total_size += candidate_size

        print("\n" + "=" * 80)
        print("ECR CLEANUP SUMMARY")
        print("=" * 80)
        print(
            f"Repositories scanned: "
            f"{len(repositories)}"
        )
        print(
            f"Total cleanup candidates: "
            f"{total_candidates}"
        )
        print(
            f"Potential storage cleanup: "
            f"{bytes_to_mb(total_size):.2f} MB"
        )

        if DRY_RUN:
            print(
                "No images were deleted because "
                "dry run is enabled."
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