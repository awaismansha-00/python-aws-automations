from fabric import Connection


SERVERS = [
    {
        "host": "192.168.1.10",
        "user": "ubuntu",
        "key_filename": "/home/awais/.ssh/server-key.pem",
    },
    {
        "host": "192.168.1.11",
        "user": "ubuntu",
        "key_filename": "/home/awais/.ssh/server-key.pem",
    },
]

PACKAGES = [
    "nginx",
    "git",
    "curl",
    "unzip",
]

APP_USER = "appuser"
APP_DIRECTORY = "/opt/myapp"


def create_connection(server):
    return Connection(
        host=server["host"],
        user=server["user"],
        connect_kwargs={
            "key_filename": server["key_filename"],
        },
    )


def run_step(connection, description, command):
    print(f"Running: {description}")

    result = connection.sudo(
        command,
        hide=True,
        warn=True,
    )

    if result.failed:
        error = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Unknown error"
        )

        raise RuntimeError(
            f"{description} failed: {error}"
        )

    print(f"Completed: {description}")


def bootstrap_server(server):
    print("\n" + "=" * 70)
    print(f"BOOTSTRAPPING SERVER: {server['host']}")
    print("=" * 70)

    try:
        with create_connection(server) as connection:
            run_step(
                connection,
                "Updating package index",
                "apt-get update -y",
            )

            package_list = " ".join(PACKAGES)

            run_step(
                connection,
                "Installing required packages",
                f"DEBIAN_FRONTEND=noninteractive "
                f"apt-get install -y {package_list}",
            )

            run_step(
                connection,
                "Creating application user",
                f"id -u {APP_USER} >/dev/null 2>&1 "
                f"|| useradd --system --create-home "
                f"--shell /bin/bash {APP_USER}",
            )

            run_step(
                connection,
                "Creating application directory",
                f"mkdir -p {APP_DIRECTORY}",
            )

            run_step(
                connection,
                "Setting directory ownership",
                f"chown -R {APP_USER}:{APP_USER} "
                f"{APP_DIRECTORY}",
            )

            run_step(
                connection,
                "Setting directory permissions",
                f"chmod 750 {APP_DIRECTORY}",
            )

            run_step(
                connection,
                "Enabling Nginx",
                "systemctl enable nginx",
            )

            run_step(
                connection,
                "Starting Nginx",
                "systemctl start nginx",
            )

            status = connection.run(
                "systemctl is-active nginx",
                hide=True,
                warn=True,
            )

            print(f"Nginx status: {status.stdout.strip()}")

            if status.stdout.strip() == "active":
                print("Bootstrap completed successfully.")
            else:
                print(
                    "Bootstrap completed, but Nginx "
                    "is not active."
                )

    except Exception as error:
        print(f"Bootstrap failed: {error}")


def main():
    print("SERVER BOOTSTRAP AUTOMATION")
    print(f"Servers configured: {len(SERVERS)}")

    for server in SERVERS:
        bootstrap_server(server)


if __name__ == "__main__":
    main()