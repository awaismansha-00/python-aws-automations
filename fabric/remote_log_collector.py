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

SERVICE_NAME = "myapp"
APPLICATION_LOG = "/var/log/myapp/application.log"
LOG_LINES = 500

LOCAL_OUTPUT_DIRECTORY = Path("collected_logs")


def create_connection(server):
    return Connection(
        host=server["host"],
        user=server["user"],
        connect_kwargs={
            "key_filename": server["key_filename"],
        },
    )


def run_remote_command(connection, command, use_sudo=False):
    if use_sudo:
        result = connection.sudo(
            command,
            hide=True,
            warn=True,
        )
    else:
        result = connection.run(
            command,
            hide=True,
            warn=True,
        )

    if result.failed:
        return (
            "Command failed:\n"
            + (
                result.stderr.strip()
                or result.stdout.strip()
                or "Unknown error"
            )
        )

    return result.stdout.strip()


def collect_application_log(connection):
    command = (
        f"test -f '{APPLICATION_LOG}' "
        f"&& tail -n {LOG_LINES} '{APPLICATION_LOG}'"
    )

    return run_remote_command(
        connection,
        command,
        use_sudo=True,
    )


def collect_service_logs(connection):
    command = (
        f"journalctl -u {SERVICE_NAME} "
        f"-n {LOG_LINES} "
        f"--no-pager"
    )

    return run_remote_command(
        connection,
        command,
        use_sudo=True,
    )


def collect_system_errors(connection):
    command = (
        f"journalctl -p err "
        f"-n {LOG_LINES} "
        f"--no-pager"
    )

    return run_remote_command(
        connection,
        command,
        use_sudo=True,
    )


def save_logs(host, application_log, service_logs, system_errors):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_host = host.replace(".", "_")

    server_directory = (
        LOCAL_OUTPUT_DIRECTORY
        / f"{safe_host}_{timestamp}"
    )

    server_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = {
        "application.log": application_log,
        "service.log": service_logs,
        "system_errors.log": system_errors,
    }

    for filename, content in files.items():
        file_path = server_directory / filename

        file_path.write_text(
            content or "No log output found.",
            encoding="utf-8",
        )

    return server_directory


def collect_logs_from_server(server):
    print("\n" + "=" * 70)
    print(f"SERVER: {server['host']}")
    print("=" * 70)

    try:
        with create_connection(server) as connection:
            print("Collecting application log...")
            application_log = collect_application_log(
                connection
            )

            print("Collecting service logs...")
            service_logs = collect_service_logs(
                connection
            )

            print("Collecting system errors...")
            system_errors = collect_system_errors(
                connection
            )

        output_directory = save_logs(
            server["host"],
            application_log,
            service_logs,
            system_errors,
        )

        print(f"Logs saved to: {output_directory}")

    except Exception as error:
        print(f"Log collection failed: {error}")


def main():
    print("REMOTE APPLICATION LOG COLLECTOR")
    print(f"Servers configured: {len(SERVERS)}")
    print(f"Service: {SERVICE_NAME}")
    print(f"Application log: {APPLICATION_LOG}")

    for server in SERVERS:
        collect_logs_from_server(server)


if __name__ == "__main__":
    main()