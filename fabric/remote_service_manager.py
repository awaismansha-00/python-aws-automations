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

SERVICE_NAME = "nginx"

# Available actions:
# status, start, stop, restart, reload
ACTION = "restart"


def create_connection(server):
    return Connection(
        host=server["host"],
        user=server["user"],
        connect_kwargs={
            "key_filename": server["key_filename"],
        },
    )


def get_service_status(connection):
    result = connection.run(
        f"systemctl is-active {SERVICE_NAME}",
        hide=True,
        warn=True,
    )

    return result.stdout.strip()


def manage_service(connection):
    if ACTION == "status":
        return

    valid_actions = {
        "start",
        "stop",
        "restart",
        "reload",
    }

    if ACTION not in valid_actions:
        raise ValueError(
            f"Invalid action '{ACTION}'. "
            f"Use status, start, stop, restart or reload."
        )

    result = connection.sudo(
        f"systemctl {ACTION} {SERVICE_NAME}",
        hide=True,
        warn=True,
    )

    if result.failed:
        error_message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Unknown error"
        )

        raise RuntimeError(
            f"Failed to {ACTION} {SERVICE_NAME}: "
            f"{error_message}"
        )


def verify_service(final_status):
    if ACTION in {"start", "restart", "reload"}:
        return final_status == "active"

    if ACTION == "stop":
        return final_status == "inactive"

    return True


def process_server(server):
    print("\n" + "=" * 70)
    print(f"SERVER: {server['host']}")
    print("=" * 70)

    connection = create_connection(server)

    try:
        connection.open()

        initial_status = get_service_status(connection)
        print(f"Initial status: {initial_status}")

        manage_service(connection)

        final_status = get_service_status(connection)
        print(f"Final status: {final_status}")

        if verify_service(final_status):
            print(
                f"SUCCESS: {SERVICE_NAME} action "
                f"'{ACTION}' completed."
            )
        else:
            print(
                f"FAILED: {SERVICE_NAME} did not reach "
                f"the expected state."
            )

    except Exception as error:
        print(f"Error: {error}")

    finally:
        connection.close()


def main():
    print("REMOTE SERVICE MANAGER")
    print(f"Service: {SERVICE_NAME}")
    print(f"Action: {ACTION}")
    print(f"Servers: {len(SERVERS)}")

    for server in SERVERS:
        process_server(server)


if __name__ == "__main__":
    main()