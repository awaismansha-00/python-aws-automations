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

SERVICE_NAME = "nginx"
LOG_LINES = 100
OUTPUT_DIRECTORY = Path("diagnostic_reports")


def create_connection(server):
    return Connection(
        host=server["host"],
        user=server["user"],
        connect_kwargs={
            "key_filename": server["key_filename"],
        },
    )


def run_command(connection, command, sudo=False):
    if sudo:
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
            f"Command failed\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    return result.stdout.strip()


def collect_diagnostics(connection):
    commands = {
        "Hostname": "hostname",
        "Current Time": "date",
        "Uptime": "uptime",
        "Memory Usage": "free -h",
        "Disk Usage": "df -h",
        "CPU Load": "cat /proc/loadavg",
        "Top Processes": "ps aux --sort=-%cpu | head -10",
        "Failed Services": "systemctl --failed --no-legend",
        f"{SERVICE_NAME} Status": (
            f"systemctl status {SERVICE_NAME} --no-pager"
        ),
        f"{SERVICE_NAME} Logs": (
            f"journalctl -u {SERVICE_NAME} "
            f"-n {LOG_LINES} --no-pager"
        ),
        "Recent System Errors": (
            f"journalctl -p err -n {LOG_LINES} --no-pager"
        ),
    }

    diagnostics = {}

    for section, command in commands.items():
        diagnostics[section] = run_command(
            connection,
            command,
            sudo=command.startswith("journalctl"),
        )

    return diagnostics


def save_report(host, diagnostics):
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    safe_host = host.replace(".", "_")

    report_path = OUTPUT_DIRECTORY / (
        f"{safe_host}_{timestamp}.txt"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as report:
        report.write(
            f"INCIDENT DIAGNOSTIC REPORT\n"
            f"Host: {host}\n"
            f"Generated: {datetime.now()}\n"
            f"{'=' * 70}\n"
        )

        for section, output in diagnostics.items():
            report.write(
                f"\n\n{section.upper()}\n"
                f"{'-' * 70}\n"
                f"{output or 'No output'}\n"
            )

    return report_path


def process_server(server):
    print("\n" + "=" * 70)
    print(f"Collecting diagnostics from: {server['host']}")
    print("=" * 70)

    try:
        with create_connection(server) as connection:
            diagnostics = collect_diagnostics(
                connection
            )

        report_path = save_report(
            server["host"],
            diagnostics,
        )

        print(f"Report saved: {report_path}")

    except Exception as error:
        print(
            f"Failed to collect diagnostics: {error}"
        )


def main():
    print("INCIDENT DIAGNOSTICS COLLECTOR")
    print(f"Servers configured: {len(SERVERS)}")

    for server in SERVERS:
        process_server(server)


if __name__ == "__main__":
    main()