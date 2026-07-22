from datetime import datetime
from pathlib import Path

from fabric import Connection


SERVERS = [
    {
        "host": "192.168.1.10",
        "user": "ubuntu",
        "key_filename": "/path/to/server-key.pem",
    },
    {
        "host": "192.168.1.11",
        "user": "ubuntu",
        "key_filename": "/path/to/server-key.pem",
    },
]

LOCAL_CONFIG = Path("nginx/myapp.conf")
REMOTE_CONFIG = "/etc/nginx/sites-available/myapp.conf"
TEMP_CONFIG = "/tmp/myapp.conf"


def create_connection(server):
    return Connection(
        host=server["host"],
        user=server["user"],
        connect_kwargs={
            "key_filename": server["key_filename"],
        },
    )


def upload_config(connection):
    connection.put(
        str(LOCAL_CONFIG),
        remote=TEMP_CONFIG,
    )

    print("New configuration uploaded to temporary location.")


def backup_current_config(connection):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{REMOTE_CONFIG}.{timestamp}.backup"

    result = connection.sudo(
        f"test -f {REMOTE_CONFIG} && "
        f"cp {REMOTE_CONFIG} {backup_path}",
        hide=True,
        warn=True,
    )

    if result.ok:
        print(f"Current configuration backed up: {backup_path}")
        return backup_path

    print("No existing configuration found to back up.")
    return None


def install_new_config(connection):
    connection.sudo(
        f"cp {TEMP_CONFIG} {REMOTE_CONFIG}"
    )

    connection.sudo(
        f"chown root:root {REMOTE_CONFIG}"
    )

    connection.sudo(
        f"chmod 644 {REMOTE_CONFIG}"
    )

    print("New configuration installed.")


def validate_nginx(connection):
    result = connection.sudo(
        "nginx -t",
        hide=True,
        warn=True,
    )

    if result.ok:
        print("Nginx configuration is valid.")
        return True

    print("Nginx validation failed.")
    print(result.stderr.strip() or result.stdout.strip())

    return False


def restore_backup(connection, backup_path):
    if not backup_path:
        connection.sudo(
            f"rm -f {REMOTE_CONFIG}"
        )

        print("Invalid configuration removed.")
        return

    connection.sudo(
        f"cp {backup_path} {REMOTE_CONFIG}"
    )

    print("Previous configuration restored.")


def reload_nginx(connection):
    result = connection.sudo(
        "systemctl reload nginx",
        hide=True,
        warn=True,
    )

    if result.failed:
        raise RuntimeError(
            result.stderr.strip()
            or "Nginx reload failed."
        )

    print("Nginx reloaded successfully.")


def cleanup(connection):
    connection.sudo(
        f"rm -f {TEMP_CONFIG}",
        hide=True,
        warn=True,
    )


def deploy_to_server(server):
    print("\n" + "=" * 70)
    print(f"SERVER: {server['host']}")
    print("=" * 70)

    try:
        with create_connection(server) as connection:
            upload_config(connection)

            backup_path = backup_current_config(
                connection
            )

            install_new_config(connection)

            if validate_nginx(connection):
                reload_nginx(connection)
                print("Configuration deployment completed.")
            else:
                restore_backup(
                    connection,
                    backup_path,
                )

                if validate_nginx(connection):
                    reload_nginx(connection)

                print("Deployment rolled back.")

            cleanup(connection)

    except Exception as error:
        print(f"Deployment failed: {error}")


def main():
    if not LOCAL_CONFIG.exists():
        print(
            f"Local configuration not found: "
            f"{LOCAL_CONFIG}"
        )
        return

    print("NGINX CONFIGURATION DEPLOYMENT")
    print(f"Servers configured: {len(SERVERS)}")

    for server in SERVERS:
        deploy_to_server(server)


if __name__ == "__main__":
    main()