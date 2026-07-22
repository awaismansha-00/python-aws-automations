# YAML Automation with PyYAML

[← Back to Main README](../README.md)

This module provides Python scripts for reading, auditing, validating, and updating YAML configuration files (such as Kubernetes manifests and GitHub Actions workflows) using **PyYAML**.

---

## ⚡ Setup & Dependencies

1. **Install PyYAML**:
   ```bash
   pip install pyyaml
   ```

2. **Core Library API Functions**:
   ```python
   import yaml

   # Load single document safely
   data = yaml.safe_load(file_stream)

   # Load multi-document YAML (e.g., K8s manifests separated by '---')
   documents = list(yaml.safe_load_all(file_stream))

   # Dump Python dict to YAML format
   yaml.safe_dump(data, file_stream, sort_keys=False)
   ```

---

## 💡 Technical Patterns & Practices

### 1. Safe Loading (`yaml.safe_load`)
Always use `safe_load()` and `safe_load_all()` instead of `load()` to prevent arbitrary Python code execution from untrusted YAML files.

### 2. Handling Multi-Document YAML Files
Kubernetes manifests often bundle multiple resources in a single file separated by `---`. Use `safe_load_all()` to parse all resources cleanly:
```python
with open("deployment.yaml") as f:
    docs = [doc for doc in yaml.safe_load_all(f) if doc is not None]
```

### 3. CI/CD Pipeline Exit Codes
Auditing scripts (`kubernetes_manifest_auditor.py` and `githubactions_workflow_auditor.py`) return explicit exit codes suitable for CI/CD gates:
* **`0`**: Compliance check passed (no policy violations).
* **`1`**: Security or reliability findings detected.

### 4. Preservation & Backup Rules
`bulk_manifest_updater.py` creates a `.backup` copy of original files before mutating YAML structures. Note that PyYAML may strip comments upon rewriting; for round-trip comment preservation, consider `ruamel.yaml`.