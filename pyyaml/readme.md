# YAML Automation with PyYAML

This folder contains Python scripts for reading, validating and updating YAML configuration files using PyYAML.

The scripts focus on practical DevOps use cases involving:

- Kubernetes manifests
- Container image updates
- GitHub Actions workflows
- CI/CD validation
- Security and reliability checks

## Requirements

Install PyYAML:

pip install pyyaml

PyYAML converts YAML files into Python dictionaries and lists.

The main functions used in these scripts are:

yaml.safe_load()
yaml.safe_load_all()
yaml.safe_dump()
yaml.safe_dump_all()

The safe functions should be used when reading YAML files because they avoid loading unsafe Python objects.

---

## Scripts

### kubernetes_manifest_auditor.py

Audits Kubernetes Deployment manifests against basic reliability, security and operational requirements.

It checks:

- Namespace configuration
- Required labels
- Explicit replica count
- Minimum replica count
- Approved container image registries
- CPU requests
- CPU limits
- Memory requests
- Memory limits
- Readiness probes
- Liveness probes
- Pod security context
- Container security context
- runAsNonRoot
- allowPrivilegeEscalation

The script:

- Scans all .yaml and .yml files inside the configured directory
- Searches subdirectories recursively
- Supports files containing multiple YAML documents
- Audits only resources where kind is Deployment
- Ignores Services, ConfigMaps, Ingress resources and other Kubernetes objects
- Prints findings with HIGH, MEDIUM and LOW severity labels
- Returns a CI/CD-compatible exit code

Exit codes:

0 = no findings detected
1 = one or more findings detected

This allows the script to run inside GitHub Actions or another CI/CD pipeline.

Example checks include:

- Missing resource limits
- Missing readiness or liveness probes
- Containers running without runAsNonRoot
- Containers allowing privilege escalation
- Images pulled from an unapproved registry
- Missing namespace or labels

The severity levels are custom policy levels and are not official Kubernetes severity ratings.

---

### bulk_manifest_updater.py

Updates a selected container image across multiple Kubernetes Deployment manifests.

The script:

- Scans all .yaml and .yml files recursively
- Loads single-document and multi-document YAML files
- Selects resources where kind is Deployment
- Finds a container using its configured name
- Replaces the existing image with a new image
- Creates a backup before modifying the original file
- Writes the updated YAML back to disk
- Reports how many files were scanned and updated

Example configuration:

CONTAINER_NAME = "myapp"

NEW_IMAGE = "123456789012.dkr.ecr.eu-west-2.amazonaws.com/myapp:v2.0.0"

Example update:

Before:

containers:
  - name: myapp
    image: myapp:v1.0.0

After:

containers:
  - name: myapp
    image: 123456789012.dkr.ecr.eu-west-2.amazonaws.com/myapp:v2.0.0

The script creates backup files such as:

deployment.yaml.backup

This makes it easier to restore the original manifest if the update is incorrect.

The current script updates only the container whose name matches CONTAINER_NAME.

If the target image is already configured, the file is not changed.

Important limitation:

PyYAML rewrites YAML formatting when saving files and may remove comments. For exact formatting and comment preservation, a round-trip YAML library such as ruamel.yaml may be more suitable.

---

### githubactions_workflow_auditor.py

Audits GitHub Actions workflow files for common security, reliability and CI/CD configuration issues.

The script scans workflow files inside:

.github/workflows/

It checks for:

- Missing workflow name
- Missing workflow trigger
- Missing top-level permissions
- Jobs without timeout-minutes
- GitHub Actions not pinned to a full commit SHA
- Docker actions not pinned to an immutable digest
- Possible hard-coded secrets
- References to long-lived AWS credentials
- Missing recognised security-scanning tools
- Workflows without jobs

The auditor recognises common security tools such as:

- Gitleaks
- Trivy
- Checkov
- SonarQube
- CodeQL

The script flags references to AWS credential variables such as:

AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN

This encourages the use of GitHub OIDC and IAM roles instead of long-lived AWS access keys.

It also checks action references.

Example mutable reference:

actions/checkout@v4

Example full commit SHA reference:

actions/checkout@3df4ab11eba7bda6032a0b82a6bb43b11571feac

The script:

- Loads GitHub Actions YAML files
- Audits workflow-level configuration
- Audits each job
- Audits each step using the uses field
- Searches nested YAML values for possible secrets
- Prints findings
- Returns a CI/CD-compatible exit code

Exit codes:

0 = no findings detected
1 = one or more findings detected

Important limitations:

- Secret detection is heuristic and may produce false positives.
- It does not replace Gitleaks, Trivy or another dedicated scanner.
- A missing branch or workflow permission may be intentional depending on the repository.
- Full commit SHA pinning is a strict security practice and may be stronger than the policy used by some teams.
- The unquoted YAML key on may be interpreted by PyYAML as the Boolean value True because of YAML 1.1 behaviour. The script handles both forms.

---

## Running the Scripts

Run the Kubernetes manifest auditor:

python3 kubernetes_manifest_auditor.py

Run the bulk manifest updater:

python3 bulk_manifest_updater.py

Run the GitHub Actions workflow auditor:

python3 githubactions_workflow_auditor.py

Review the configuration variables at the top of each script before running it.

---

## Suggested Folder Structure

pyyaml/
├── bulk_manifest_updater.py
├── githubactions_workflow_auditor.py
├── kubernetes_manifest_auditor.py
└── README.md

Example Kubernetes directory:

kubernetes/
├── dev/
│   └── app-deployment.yaml
├── qa/
│   └── app-deployment.yaml
└── prod/
    └── app-deployment.yaml

Example GitHub Actions directory:

.github/
└── workflows/
    ├── ci.yaml
    ├── terraform.yaml
    └── deployment.yaml

---

## Common PyYAML Functions Used

### yaml.safe_load()

Reads one YAML document and converts it into Python dictionaries and lists.

Example:

with open("config.yaml") as file:
    data = yaml.safe_load(file)

---

### yaml.safe_load_all()

Reads multiple YAML documents from one file.

This is useful for Kubernetes files containing several resources separated by:

---

Example:

with open("manifests.yaml") as file:
    documents = list(yaml.safe_load_all(file))

---

### yaml.safe_dump()

Writes one Python dictionary to a YAML file.

Example:

with open("output.yaml", "w") as file:
    yaml.safe_dump(
        data,
        file,
        sort_keys=False
    )

---

### yaml.safe_dump_all()

Writes several Python dictionaries as multiple YAML documents.

Example:

with open("output.yaml", "w") as file:
    yaml.safe_dump_all(
        documents,
        file,
        sort_keys=False,
        explicit_start=True
    )

---

## What These Scripts Demonstrate

The scripts demonstrate practical PyYAML usage for DevOps, including:

- Reading YAML files
- Loading multiple YAML documents
- Traversing nested dictionaries and lists
- Validating required fields
- Auditing Kubernetes configurations
- Auditing GitHub Actions workflows
- Updating container image values
- Creating backups before modification
- Writing updated YAML files
- Scanning directories recursively
- Handling invalid YAML syntax
- Returning CI/CD exit codes

---

## Security and Safety Notes

- Use yaml.safe_load() and yaml.safe_load_all() instead of unsafe load functions.
- Review all manifest changes before committing them.
- Keep backup creation enabled when modifying files.
- Do not store plaintext secrets inside YAML files.
- Use Kubernetes Secrets, AWS Secrets Manager or another secret-management solution.
- Treat workflow secret detection as an additional check, not a replacement for Gitleaks.
- Test scripts against sample files before using them in production repositories.
- Review CI/CD exit-code behaviour before adding the scripts as required pipeline checks.
- Validate modified Kubernetes manifests using tools such as kubeconform or kubectl dry-run.
- Review Git changes before pushing updated YAML files.