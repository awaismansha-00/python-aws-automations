# AWS Automation with Boto3

This folder contains Python scripts for automating common AWS operational, security, monitoring, governance, backup and cost-management tasks using Boto3.

The scripts use AWS credentials already configured through the AWS CLI credential chain.

## Requirements

Install Boto3:

pip install boto3

Confirm that AWS authentication is working:

aws sts get-caller-identity

Most scripts use a region variable inside the file:

REGION = "eu-west-2"

Update the region before running a script.

---

## Scripts

### inventory.py

Creates a basic inventory of AWS resources in the configured region.

It lists:

- EC2 instances
- EBS volumes
- Elastic IP addresses
- RDS databases
- Application and Network Load Balancers
- Lambda functions
- EKS clusters
- ECR repositories

The script uses pagination where supported and displays the total number of resources found.

---

### unused_resources.py

Identifies AWS resources that may be unused or generating unnecessary cost.

It reports:

- Unattached EBS volumes
- Unassociated Elastic IP addresses
- Stopped EC2 instances
- EBS snapshots older than the configured age threshold

The script is read-only and does not delete any resources.

---

### ec2_scheduler.py

Starts or stops selected EC2 instances.

Only instances containing the configured tag are managed:

AutoSchedule=true

Supported operations include:

- Starting stopped instances
- Stopping running instances
- Previewing changes using dry-run mode

The tag filter prevents the script from modifying every EC2 instance in the region.

---

### ebs_snapshot_manager.py

Creates and audits EBS snapshots.

It selects volumes tagged with:

Backup=true

Supported actions include:

- Creating snapshots
- Adding metadata tags to snapshots
- Listing snapshots owned by the AWS account
- Identifying snapshots older than the configured retention period

The current version reports old snapshots but does not delete them automatically.

---

### cost_report.py

Generates an AWS cost report using Cost Explorer.

It:

- Retrieves costs for the current month
- Groups costs by AWS service
- Removes services with zero cost
- Sorts services from highest to lowest cost
- Calculates the total AWS cost

AWS billing data may be delayed and should not be treated as real-time information.

---

### tag_compliance_checker.py

Checks AWS resources for required tags.

Example required tags:

Environment
Owner
Project
ManagedBy

The script:

- Retrieves resources through the Resource Groups Tagging API
- Identifies missing tags
- Reports compliant and non-compliant resources
- Calculates a compliance percentage

Some AWS resource types may not be returned by the Resource Groups Tagging API and may require service-specific APIs.

---

### security_group_auditor.py

Audits EC2 security-group inbound rules.

It detects:

- Public IPv4 access from 0.0.0.0/0
- Public IPv6 access from ::/0
- Unrestricted access to all protocols and ports
- Publicly exposed sensitive ports

Sensitive ports include:

- SSH: 22
- RDP: 3389
- MySQL: 3306
- PostgreSQL: 5432
- Redis: 6379
- Elasticsearch: 9200

The script reports findings with basic severity levels but does not modify security-group rules.

---

### iam_security_auditor.py

Performs a read-only IAM user security audit.

It checks for:

- Console users without MFA
- Old access keys
- Access keys that have never been used
- Access keys that have not been used recently
- Managed policies attached directly to IAM users

IAM is a global AWS service, so this script does not require a region variable.

---

### cloudwatch_alarm_auditor.py

Checks whether EC2 instances have expected CloudWatch alarms.

The default checks include:

- CPUUtilization
- StatusCheckFailed

The script reports:

- Existing alarms
- Missing alarms
- Alarm states
- Actions-enabled status
- Alarm compliance percentage

The script currently checks whether an alarm exists but does not fully validate its thresholds, evaluation periods or SNS actions.

---

### cloudwatch_health_report.py

Generates an operational health report for running EC2 instances.

It collects:

- Average CPU utilisation
- Maximum CPU utilisation
- EC2 status-check failures
- CloudWatch alarms currently in the ALARM state

Each instance is classified as:

- HEALTHY
- WARNING
- CRITICAL
- NO DATA

The health thresholds can be configured inside the script.

---

### ssm_remote_health_check.py

Runs remote health checks on Linux EC2 instances using AWS Systems Manager.

It collects:

- Hostname
- Uptime
- Memory usage
- Disk usage
- CPU load

This avoids direct SSH access.

The target instances must:

- Be registered with Systems Manager
- Have SSM Agent installed and running
- Have the required IAM instance profile
- Have connectivity to the required SSM endpoints

---

### ecr_image_cleanup.py

Audits Amazon ECR repositories for old container images.

It detects:

- Untagged images older than the configured threshold
- Tagged images older than the configured threshold
- Images beyond the configured number of retained releases

Protected tags include:

latest
prod
production
stable

Dry-run mode is enabled by default. Images are deleted only after explicitly disabling dry-run mode.

---

### lambda_rollback.py

Rolls back a Lambda alias to an older published version.

It:

- Retrieves the current alias version
- Lists published Lambda versions
- Checks whether the target version exists
- Previews the rollback in dry-run mode
- Updates the alias when execution is enabled

The script changes the alias pointer rather than modifying the Lambda function code.

---

### route53_acm_auditor.py

Audits Route 53 hosted zones and ACM certificates.

Route 53 checks include:

- Listing hosted zones
- Listing DNS records
- Displaying record types and targets

ACM checks include:

- Certificate status
- Expiry date
- Remaining days before expiration
- Certificates not attached to AWS resources

Route 53 is global, while ACM certificates are regional.

---

### s3_governance_auditor.py

Audits S3 buckets against common governance and security controls.

It checks:

- Block Public Access settings
- Default encryption
- Versioning
- Server access logging
- Lifecycle policies

The script only reports findings and does not modify bucket settings.

---

### multiaccount_inventory.py

Scans EC2 instances across multiple AWS accounts in AWS Organizations.

It:

- Lists active organization accounts
- Assumes a configured IAM role in each account
- Creates temporary cross-account credentials
- Lists EC2 instances in the configured region
- Continues scanning when an account cannot be accessed

This script requires:

- AWS Organizations
- Access from the management account or delegated administrator
- A trusted IAM role in each member account
- Permission to call sts:AssumeRole

---

## Running a Script

Run any script directly:

python3 inventory.py

Example:

python3 security_group_auditor.py

Review the configuration variables at the top of every script before running it.

---

## Safety Notes

- Test scripts in a non-production AWS account first.
- Keep dry-run mode enabled for scripts that can make changes.
- Do not assume that an old or unattached resource is safe to delete.
- Review tags, dependencies and business requirements before remediation.
- Avoid hard-coded AWS credentials.
- Prefer IAM roles and least-privilege permissions in production.
- Use pagination for AWS list and describe operations.
- Expect API throttling in large accounts.
- Review all destructive actions before execution.