from pathlib import Path
from shutil import copy2

import yaml


MANIFEST_DIRECTORY = Path("kubernetes")

CONTAINER_NAME = "myapp"
NEW_IMAGE = "123456789012.dkr.ecr.eu-west-2.amazonaws.com/myapp:v2.0.0"

CREATE_BACKUP = True


def load_yaml_documents(file_path):
    with file_path.open("r", encoding="utf-8") as file:
        return list(yaml.safe_load_all(file))


def save_yaml_documents(file_path, documents):
    with file_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump_all(
            documents,
            file,
            sort_keys=False,
            explicit_start=True,
        )


def create_backup(file_path):
    backup_path = file_path.with_suffix(
        file_path.suffix + ".backup"
    )

    copy2(file_path, backup_path)

    return backup_path


def update_deployment(document):
    if not document:
        return False

    if document.get("kind") != "Deployment":
        return False

    pod_spec = (
        document
        .get("spec", {})
        .get("template", {})
        .get("spec", {})
    )

    containers = pod_spec.get("containers", [])

    for container in containers:
        if container.get("name") == CONTAINER_NAME:
            old_image = container.get("image")

            if old_image == NEW_IMAGE:
                return False

            container["image"] = NEW_IMAGE

            print(
                f"Updated container '{CONTAINER_NAME}': "
                f"{old_image} -> {NEW_IMAGE}"
            )

            return True

    return False


def update_file(file_path):
    try:
        documents = load_yaml_documents(file_path)

    except yaml.YAMLError as error:
        print(f"Invalid YAML in {file_path}: {error}")
        return False

    file_updated = False

    for document in documents:
        if update_deployment(document):
            file_updated = True

    if not file_updated:
        return False

    if CREATE_BACKUP:
        backup_path = create_backup(file_path)
        print(f"Backup created: {backup_path}")

    save_yaml_documents(
        file_path,
        documents,
    )

    print(f"File updated: {file_path}")

    return True


def get_yaml_files():
    yaml_files = list(
        MANIFEST_DIRECTORY.rglob("*.yaml")
    )

    yaml_files.extend(
        MANIFEST_DIRECTORY.rglob("*.yml")
    )

    return sorted(set(yaml_files))


def main():
    print("BULK KUBERNETES MANIFEST UPDATER")
    print(f"Directory: {MANIFEST_DIRECTORY}")
    print(f"Container: {CONTAINER_NAME}")
    print(f"New image: {NEW_IMAGE}")

    if not MANIFEST_DIRECTORY.exists():
        print(
            f"Directory does not exist: "
            f"{MANIFEST_DIRECTORY}"
        )
        return

    yaml_files = get_yaml_files()

    if not yaml_files:
        print("No YAML files found.")
        return

    updated_files = 0

    for file_path in yaml_files:
        if update_file(file_path):
            updated_files += 1

    print("\n" + "=" * 70)
    print("UPDATE SUMMARY")
    print("=" * 70)
    print(f"Files scanned: {len(yaml_files)}")
    print(f"Files updated: {updated_files}")


if __name__ == "__main__":
    main()