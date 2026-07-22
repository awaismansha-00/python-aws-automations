# Remote Server Automation with Fabric

[← Back to Main README](../README.md)

This module contains Python scripts for executing agentless server administration, remote troubleshooting, software configuration, and log collection over SSH using **Fabric**.

---

## ⚡ Setup & Server Configuration

1. **Install Fabric**:
   ```bash
   pip install fabric
   ```

2. **Target Server Configuration**:
   Each script defines a `SERVERS` configuration list at the top:
   ```python
   SERVERS = [
       {
           "host": "192.168.1.10",
           "user": "ubuntu",
           "key_filename": "/path/to/server-key.pem",
       }
   ]
   ```
   Update the IP addresses, SSH credentials, and key paths prior to running any script.

---

## 🧰 Key Fabric Features & API Usage

### 1. Connection Object
Establishes an SSH connection to a remote server using SSH key authentication:
```python
from fabric import Connection

conn = Connection(
    host="192.168.1.10",
    user="ubuntu",
    connect_kwargs={"key_filename": "/path/to/key.pem"}
)
```

### 2. Command Execution (`run` vs `sudo`)
* **`conn.run("command")`**: Executes standard remote shell commands.
* **`conn.sudo("systemctl restart nginx")`**: Executes privileged commands with elevated permissions.

### 3. File Transfer (`put` & `get`)
* **`conn.put("local.conf", remote="/tmp/remote.conf")`**: Uploads local configuration files to remote hosts.
* **`conn.get(remote="/var/log/syslog", local="logs/syslog")`**: Downloads remote logs and diagnostic artifacts locally.

### 4. Non-Blocking Failures (`warn=True`)
Prevents a single failed command or host connection from crashing the execution loop across remaining hosts:
```python
result = conn.run("systemctl is-active nginx", warn=True)
if result.failed:
    print("Service is down!")
```

---

## 🔒 Security Best Practices

* **Key-Based Authentication**: Always use SSH private keys instead of plain-text passwords.
* **Sudo Least-Privilege**: Ensure the target user has specific `sudoers` rules for required operations (`systemctl`, `nginx -t`).
* **Validation & Rollback**: See `nginx_config_deployer.py` for an example of validating syntax (`nginx -t`) before reloading services and rolling back on failure.