# Remote Server Automation with Fabric

This folder contains Python scripts for automating common Linux server administration, troubleshooting, configuration and maintenance tasks over SSH using Fabric.

Fabric provides a higher-level interface over Paramiko and makes it easier to:

- Connect to remote Linux servers
- Run shell commands
- Execute privileged commands using sudo
- Upload and download files
- Automate tasks across multiple servers
- Validate configuration changes
- Collect logs and diagnostic information

Note: The folder is currently named paramiko, but the scripts use Fabric. Renaming the folder to fabric would make the repository structure clearer.

## Requirements

Install Fabric:

pip install fabric

Each script contains a server configuration similar to:

SERVERS = [
    {
        "host": "192.168.1.10",
        "user": "ubuntu",
        "key_filename": "/home/user/.ssh/server-key.pem",
    }
]

Before running a script, update:

- Server IP address or hostname
- SSH username
- Private-key path
- Service name
- Remote file paths where applicable

The target server must allow SSH access from your machine.

---

## Scripts

### multi_server_health_check.py

Runs a basic health check across multiple Linux servers.

It collects:

- Server uptime
- Root disk usage
- Memory usage
- Failed systemd services
- Status of a selected application service such as Nginx

The script:

- Connects to each configured server over SSH
- Runs health-check commands
- Prints the results for each server
- Continues checking other servers if one connection or command fails
- Closes each SSH connection after completion

This script is intended for quick operational checks rather than continuous monitoring.

---

### remote_service_manager.py

Manages a selected systemd service across multiple servers.

Supported actions include:

- status
- start
- stop
- restart
- reload

The script:

- Checks the initial service state
- Runs the selected systemctl operation using sudo
- Checks the service again afterward
- Verifies whether the service reached the expected state
- Reports success or failure for each server

Example configuration:

SERVICE_NAME = "nginx"
ACTION = "restart"

The remote user must have permission to run the required systemctl commands through sudo.

---

### incident_diagnostics_collector.py

Collects detailed system and application information for incident investigation.

It gathers:

- Hostname
- Current server time
- Uptime
- Memory usage
- Disk usage
- CPU load
- Highest CPU-consuming processes
- Failed systemd services
- Application service status
- Recent service logs
- Recent system-level errors

The script saves a timestamped diagnostic report locally for each server.

This is useful when:

- Investigating a production incident
- Comparing the state of several servers
- Central monitoring or logging is unavailable
- Evidence needs to be collected before making changes

The script is more detailed than the health checker and is intended for troubleshooting rather than routine monitoring.

---

### remote_log_collector.py

Collects application and system logs from multiple remote servers.

It retrieves:

- Recent application log entries
- Recent systemd service logs
- Recent system-level error messages

The logs are stored locally in separate timestamped directories for each server.

Example output structure:

collected_logs/
└── 192_168_1_10_20260722_160500/
    ├── application.log
    ├── service.log
    └── system_errors.log

This script is useful when:

- Central logging is temporarily unavailable
- Logs must be collected quickly from several VMs
- An incident requires direct server inspection
- Troubleshooting data must be saved locally

It complements centralised logging tools such as Elasticsearch, Fluent Bit and Kibana rather than replacing them.

---

### server_bootstrap.py

Performs initial preparation of fresh Ubuntu or Debian servers.

It can:

- Update the package index
- Install required packages
- Create an application user
- Create application directories
- Set directory ownership
- Configure file permissions
- Enable Nginx
- Start Nginx
- Verify the final service status

The default package list may include:

- Nginx
- Git
- curl
- unzip

The script uses apt-get and is therefore intended for Debian-based Linux distributions.

Some commands are written to be reasonably idempotent. For example, the application user is only created if it does not already exist.

This script is suitable for a small number of servers. For large environments, a dedicated configuration-management platform may be more appropriate.

---

### nginx_config_deployer.py

Safely deploys a new Nginx configuration to multiple servers.

The deployment process is:

Upload the new configuration to /tmp
→ Back up the existing configuration
→ Copy the new file into the Nginx configuration directory
→ Set the correct ownership and permissions
→ Validate the configuration using nginx -t
→ Reload Nginx when validation succeeds
→ Restore the previous configuration when validation fails
→ Remove the temporary uploaded file

The script demonstrates:

- Remote file upload using Fabric
- Privileged file operations
- Timestamped configuration backups
- Nginx syntax validation
- Safe service reload
- Basic rollback behaviour

The remote user must have sudo permission for commands such as:

- cp
- chown
- chmod
- nginx -t
- systemctl reload nginx

The script should first be tested against a non-production server.

---

## Running a Script

Run any script directly:

python3 multi_server_health_check.py

Examples:

python3 remote_service_manager.py

python3 incident_diagnostics_collector.py

python3 remote_log_collector.py

python3 server_bootstrap.py

python3 nginx_config_deployer.py

Review all configuration variables at the top of each script before running it.

---

## Common Fabric Methods Used

### Connection

Creates an SSH connection to a remote server.

Example:

Connection(
    host="192.168.1.10",
    user="ubuntu",
    connect_kwargs={
        "key_filename": "/home/user/.ssh/server-key.pem"
    }
)

### run()

Runs a normal remote shell command.

Example:

connection.run("uptime")

### sudo()

Runs a remote command with elevated privileges.

Example:

connection.sudo("systemctl restart nginx")

### put()

Uploads a local file to the remote server.

Example:

connection.put(
    "myapp.conf",
    remote="/tmp/myapp.conf"
)

### get()

Downloads a remote file to the local machine.

Example:

connection.get(
    remote="/var/log/myapp.log",
    local="logs/myapp.log"
)

### warn=True

Prevents one failed command from immediately stopping the entire script.

Example:

connection.run(
    "systemctl is-active nginx",
    warn=True
)

---

## When Fabric Is Appropriate

Fabric is useful for:

- Small VM-based environments
- Custom SSH automation
- Ad hoc server maintenance
- Legacy Linux servers
- Direct troubleshooting
- Configuration deployment
- Collecting logs and diagnostics
- Managing a limited number of servers

Fabric is less suitable for:

- Kubernetes deployments
- Large-scale infrastructure provisioning
- Continuous monitoring
- Centralised logging
- Managing hundreds of servers
- GitOps workflows
- AWS operations that can be handled through Systems Manager or AWS APIs

For Kubernetes workloads, use Kubernetes, CI/CD or GitOps tools.

For AWS EC2 operations, AWS Systems Manager may be preferable because it avoids direct SSH access.

---

## Security Notes

- Never commit private SSH keys to Git.
- Do not hard-code passwords in scripts.
- Use key-based SSH authentication.
- Restrict port 22 to trusted IP addresses.
- Use least-privilege sudo permissions.
- Validate remote paths before copying or deleting files.
- Test scripts on non-production servers first.
- Avoid running destructive commands without confirmation.
- Review command output and error handling before production use.
- Rotate SSH keys when team members or access requirements change.
- Keep host-key verification enabled where possible.

---

## Limitations

- The current scripts process servers sequentially.
- Connection failures are handled per server, but retry logic is limited.
- Most scripts assume Linux with systemd.
- The bootstrap script assumes Ubuntu or Debian.
- Some commands require passwordless or appropriately configured sudo access.
- Fabric automation depends on SSH connectivity.
- Direct SSH may not be allowed in highly restricted cloud environments.
- These scripts do not maintain a persistent desired state.
- Repeated manual configuration changes can create drift between servers.