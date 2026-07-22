from fabric import Connection
from invoke.exceptions import UnexpectedExit


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

SERVICE_NAME = "nginx"


def create_connection(server):
    return Connection(
        host=server["host"],
        user=server["user"],
        connect_kwargs={
            "key_filename": server["key_filename"],
        },
    )


def run_command(connection, command):
    result = connection.run(
        command,
        hide=True,
        warn=True,
    )

    if result.failed:
        return f"Command failed: {result.stderr.strip()}"

    return result.stdout.strip()


def check_server(server):
    print("\n" + "=" * 70)
    print(f"SERVER: {server['host']}")
    print("=" * 70)

    connection = create_connection(server)

    try:
        connection.open()

        uptime = run_command(
            connection,
            "uptime -p",
        )

        disk_usage = run_command(
            connection,
            "df -h / | tail -1",
        )

        memory_usage = run_command(
            connection,
            "free -h | grep Mem",
        )

        failed_services = run_command(
            connection,
            "systemctl --failed --no-legend",
        )

        service_status = run_command(
            connection,
            f"systemctl is-active {SERVICE_NAME}",
        )

        print(f"Uptime: {uptime}")
        print(f"Disk: {disk_usage}")
        print(f"Memory: {memory_usage}")
        print(f"{SERVICE_NAME} status: {service_status}")

        print("\nFailed services:")

        if failed_services:
            print(failed_services)
        else:
            print("None")

    except UnexpectedExit as error:
        print(
            f"Remote command failed: "
            f"{error.result.stderr}"
        )

    except Exception as error:
        print(f"Connection failed: {error}")

    finally:
        connection.close()


def main():
    print("MULTI-SERVER HEALTH CHECK")
    print(f"Servers configured: {len(SERVERS)}")

    for server in SERVERS:
        check_server(server)


if __name__ == "__main__":
    main()