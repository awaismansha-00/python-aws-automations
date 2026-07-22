# AWS Automation with Boto3

[← Back to Main README](../README.md)

This module provides Python automation scripts for AWS operations, auditing, monitoring, and cost management using the **Boto3** SDK.

---

## ⚡ Prerequisites & Authentication

1. **Install Boto3**:
   ```bash
   pip install boto3
   ```

2. **AWS Authentication**:
   Scripts rely on the standard AWS CLI credential chain (`~/.aws/credentials`, environment variables, or IAM instance profiles/roles). Verify authentication before running:
   ```bash
   aws sts get-caller-identity
   ```

3. **Region Configuration**:
   Most scripts define a `REGION` variable at the top of the file:
   ```python
   REGION = "eu-west-2"
   ```
   Update this variable to target your desired AWS region before execution.

---

## ⚙️ Key Configuration & Tagging Conventions

| Script | Key Controls & Required Tags |
| :--- | :--- |
| **`ec2_scheduler.py`** | Manages instances tagged with `AutoSchedule=true`. Supports dry-run mode. |
| **`ebs_snapshot_manager.py`** | Backs up volumes tagged with `Backup=true`. Checks retention thresholds. |
| **`tag_compliance_checker.py`** | Audits presence of `Environment`, `Owner`, `Project`, `ManagedBy`. |
| **`ecr_image_cleanup.py`** | Protects tags `latest`, `prod`, `production`, `stable`. Dry-run enabled by default. |
| **`multiaccount_inventory.py`** | Requires AWS Organizations and an assume-role IAM role name across member accounts. |

---

## 💡 Key Boto3 Patterns Demonstrated

* **Pagination**: Utilizes Boto3 paginators (`get_paginator('list_objects_v2')`) to safely retrieve large resource lists without hitting truncation limits.
* **Dry-Run Protections**: Uses native dry-run capabilities (or script-level dry-run flags) prior to executing state-changing operations.
* **Cross-Account Access**: Leverages `boto3.client('sts').assume_role()` for multi-account governance.
* **Error Handling**: Catches `botocore.exceptions.ClientError` for graceful API throttling and access permission handling.

---

## 🛡️ Safety & Operational Limitations

For specific caveats regarding API pagination, asynchronous operations, and cost Explorer billing delays, refer to **[Limitations.txt](../Limitations.txt)**.