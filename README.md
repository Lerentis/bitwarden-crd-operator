# Bitwarden CRD Operator

[![Build Status](https://drone.uploadfilter24.eu/api/badges/lerentis/bitwarden-crd-operator/status.svg?ref=refs/heads/main)](https://drone.uploadfilter24.eu/lerentis/bitwarden-crd-operator) [![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/lerentis)](https://artifacthub.io/packages/search?repo=lerentis)

<p align="center">
  <img src="logo.png" alt="Bitwarden CRD Operator Logo" width="200"/>
</p>

A Kubernetes operator that synchronizes secrets from Bitwarden into Kubernetes Secret objects. Built with [kopf](https://github.com/nolar/kopf/) and powered by the Bitwarden CLI, this operator enables GitOps-friendly secret management by allowing you to define secrets as Kubernetes Custom Resources while keeping sensitive data secure in Bitwarden.

## Features

- 🔐 **Automatic Secret Synchronization** - Sync secrets from Bitwarden to Kubernetes automatically
- 🔄 **Continuous Updates** - Configurable sync intervals keep secrets up-to-date
- 🎯 **Multiple Secret Types** - Support for generic secrets, registry credentials, and templated configurations
- 📝 **Template Engine** - Use Jinja2 templates with Bitwarden lookups for complex configurations
- 🏷️ **Custom Labels & Annotations** - Add metadata to generated secrets
- 🗑️ **Garbage Collection** - Automatic cleanup of managed secrets when CRDs are deleted
- 🔒 **Self-hosted & SaaS** - Works with both Bitwarden SaaS and self-hosted instances
- ⚡ **Efficient CLI usage** - Uses the Bitwarden CLI efficiently for session handling and syncs

> **Note:** This operator uses the Bitwarden CLI. For local testing you can install it from the official project or use the bundled CLI inside the operator image.


## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Wording](#wording)
  - [BitwardenSecret](#bitwardensecret)
  - [RegistryCredential](#registrycredential)
  - [BitwardenTemplate](#bitwardentemplate)
- [Configuration](#configuration)
- [Examples](#examples)

## Prerequisites

Before installing the operator, you'll need:

1. **Bitwarden Account** - Either SaaS or self-hosted instance
2. **Email Address** - Your Bitwarden account email
3. **Master Password** - Your Bitwarden master password
4. **Kubernetes Cluster** - Version 1.16+ recommended
5. **Bitwarden CLI** - The operator container includes the Bitwarden CLI, but for local testing you can install it from the official Bitwarden CLI releases or your package manager

## Installation

### Step 1: Prepare Credentials

You will need a `ClientID` and `ClientSecret` ([where to get these](https://bitwarden.com/help/personal-api-key/)) as well as your password.  
You have two options for providing Bitwarden credentials:

#### Option A: Using Helm Values (Quick Start)

Create a `values.yaml` file:

```yaml
env:
  - name: BW_EMAIL
    value: "your-email@example.com"
  - name: BW_PASSWORD
    value: "YourSuperSecurePassword"
  - name: BW_CLIENTID
    value: "user.your-client-id"
  - name: BW_CLIENTSECRET
    value: "YoUrCliEntSecRet"
  # Optional: for self-hosted Bitwarden
  - name: BW_HOST
    value: "https://bitwarden.your.tld.org"
  # Optional: custom identity URL
  - name: BW_IDENTITY_URL
    value: "https://identity.your.tld.org"
x
```

#### Option B: Using Existing Secret (Recommended for Production)

Create a Kubernetes secret with your credentials:

```bash
kubectl create namespace bw-operator

kubectl create secret generic bitwarden-credentials \
  --namespace bw-operator \
  --from-literal=BW_EMAIL='your-email@example.com' \
  --from-literal=BW_PASSWORD='YourSuperSecurePassword' \
  --from-literal=BW_CLIENTID='user.your-client-id' \
  --from-literal=BW_CLIENTSECRET='YoUrCliEntSecRet'
  # Optional for self-hosted:
  # --from-literal=BW_HOST='https://bitwarden.your.tld.org'
```

Then reference it in `values.yaml`:

```yaml
externalConfigSecret:
  enabled: true
  name: "bitwarden-credentials"
```

### Step 2: Install the Operator

```bash
# Add the Helm repository
helm repo add bitwarden-operator https://lerentis.github.io/bitwarden-crd-operator
helm repo update

# Create namespace
kubectl create namespace bw-operator

# Install the operator
helm upgrade --install \
  --namespace bw-operator \
  -f values.yaml \
  bw-operator \
  bitwarden-operator/bitwarden-crd-operator
```

### Step 3: Verify Installation

```bash
# Check if the operator is running
kubectl get pods -n bw-operator

# Check operator logs
kubectl logs -n bw-operator -l app.kubernetes.io/name=bitwarden-crd-operator
```

## Usage

### Wording

The Bitwarden API distinguishes between simple login entries (username/password), custom fields, and attachments; the operator exposes these via the `secretScope` setting to control how items are mapped into Kubernetes Secrets.

- login — Use when you need the entry's username or password; specify `secretScope: login` .
- fields — Use for custom key/value fields stored on an item; specify `secretScope: fields` .
- attachment — Use for files attached to a Bitwarden item; specify `secretScope: attachment` .

#### Examples

Login entry:

```yaml
  - element:
      secretName: username
      secretRef: my-username-key
      secretScope: login
```

Custom field:

```yaml
  - element:
      secretName: api_key
      secretRef: my-api-key
      secretScope: fields
```

Attachment (file):

```yaml
  - element:
      secretName: some-file.txt
      secretRef: file-key
      secretScope: attachment
```

### BitwardenSecret

The `BitwardenSecret` custom resource allows you to map specific fields from a Bitwarden item to a Kubernetes Secret.

#### How to Find Your Bitwarden Item ID

1. Open your Bitwarden vault in a web browser
2. Click on the item you want to use
3. Look at the URL - the ID is the last part: `https://vault.bitwarden.com/#/vault?itemId=YOUR-ITEM-ID`

#### Basic Example

```yaml
apiVersion: "lerentis.uploadfilter24.eu/v1beta8"
kind: BitwardenSecret
metadata:
  name: example-secret
  namespace: default
spec:
  content:
    - element:
        secretName: username          # Field name in Bitwarden
        secretRef: db-username        # Key name in Kubernetes Secret
        secretScope: login            # Scope: login, fields, or attachment
    - element:
        secretName: password
        secretRef: db-password
        secretScope: login
    - element:
        secretName: api_key           # Custom field in Bitwarden
        secretRef: api-key
        secretScope: fields           # Use 'fields' for custom fields
  id: "88781348-c81c-4367-9801-550360c21295"  # Bitwarden item ID
  name: "database-credentials"                 # Name of Kubernetes Secret
  namespace: "production"                      # Target namespace
  secretType: Opaque                           # Optional: Default is Opaque
  labels:                                      # Optional
    app: myapp
    environment: production
  annotations:                                 # Optional
    custom.annotation: example-value
```

#### Field Reference

| Field | Description | Required | Default |
|-------|-------------|----------|---------|
| `id` | Bitwarden item ID | Yes | - |
| `name` | Name of the Kubernetes Secret to create | Yes | - |
| `namespace` | Target namespace for the Secret | Yes | - |
| `secretType` | Kubernetes Secret type | No | `Opaque` |
| `labels` | Labels to add to the Secret | No | `{}` |
| `annotations` | Annotations to add to the Secret | No | `{}` |
| `content[].element.secretName` | Field name in Bitwarden | Yes | - |
| `content[].element.secretRef` | Key name in Kubernetes Secret | Yes | - |
| `content[].element.secretScope` | Field scope: `login`, `fields`, or `attachment` | Yes | - |

#### Secret Scopes

- **`login`**: Use for standard login fields (`username`, `password`)
- **`fields`**: Use for custom fields you've added to the Bitwarden item
- **`attachment`**: Use for file attachments (use filename as `secretName`)

#### Resulting Secret

```yaml
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: database-credentials
  namespace: production
  labels:
    app: myapp
    environment: production
  annotations:
    managed: bitwarden-secret.lerentis.uploadfilter24.eu
    managedObject: default/example-secret
    custom.annotation: example-value
data:
  db-username: <base64-encoded-value>
  db-password: <base64-encoded-value>
  api-key: <base64-encoded-value>
```

### RegistryCredential

The `RegistryCredential` creates Docker registry authentication secrets (pull secrets) from Bitwarden items. This is useful for authenticating with private container registries.

#### Example

```yaml
apiVersion: "lerentis.uploadfilter24.eu/v1beta8"
kind: RegistryCredential
metadata:
  name: docker-hub-credentials
  namespace: default
spec:
  usernameRef: username              # Field in Bitwarden (usually 'username')
  passwordRef: password              # Field in Bitwarden (usually 'password')
  registry: "docker.io"              # Registry URL
  id: "3b249ec7-9ce7-440a-9558-f34f3ab10680"
  name: "dockerhub-pull-secret"      # Name of the Secret
  namespace: "production"            # Target namespace
  labels:
    app: myapp
  annotations:
    description: "Docker Hub credentials"
```

#### Common Registries

| Registry | URL |
|----------|-----|
| Docker Hub | `docker.io` or `https://index.docker.io/v1/` |
| GitHub Container Registry | `ghcr.io` |
| Google Container Registry | `gcr.io` |
| Amazon ECR | `<account-id>.dkr.ecr.<region>.amazonaws.com` |
| Azure Container Registry | `<registry-name>.azurecr.io` |

#### Using the Pull Secret

Reference the created secret in your Pod spec:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  imagePullSecrets:
    - name: dockerhub-pull-secret
  containers:
    - name: app
      image: my-private-repo/my-app:latest
```

#### Resulting Secret

```yaml
apiVersion: v1
kind: Secret
type: kubernetes.io/dockerconfigjson
metadata:
  name: dockerhub-pull-secret
  namespace: production
  annotations:
    managed: registry-credential.lerentis.uploadfilter24.eu
    managedObject: default/docker-hub-credentials
data:
  .dockerconfigjson: <base64-encoded-docker-config>
```

### BitwardenTemplate

The `BitwardenTemplate` is the most flexible option, allowing you to create complex configuration files using Jinja2 templates with the `bitwarden_lookup` function to inject secrets directly from Bitwarden.

#### Use Cases

- Application configuration files with embedded secrets
- Multi-file configurations
- Complex YAML/JSON structures
- Environment-specific configurations

#### Example

```yaml
apiVersion: "lerentis.uploadfilter24.eu/v1beta8"
kind: BitwardenTemplate
metadata:
  name: app-config
  namespace: default
spec:
  name: "application-config"
  namespace: "production"
  secretType: Opaque  # Optional
  labels:
    app: myapp
  annotations:
    description: "Application configuration with secrets"
  content:
    - element:
        filename: app-config.yaml
        template: |
          database:
            host: db.example.com
            port: 5432
            username: {{ bitwarden_lookup("88781348-c81c-4367-9801-550360c21295", "login", "username") }}
            password: {{ bitwarden_lookup("88781348-c81c-4367-9801-550360c21295", "login", "password") }}
          
          api:
            enabled: true
            key: {{ bitwarden_lookup("466fc4b0-ffca-4444-8d88-b59d4de3d928", "fields", "api_key") }}
            secret: {{ bitwarden_lookup("466fc4b0-ffca-4444-8d88-b59d4de3d928", "fields", "api_secret") }}
          
          tls:
            cert: {{ bitwarden_lookup("cert-item-id", "attachment", "server.crt") }}
            key: {{ bitwarden_lookup("cert-item-id", "attachment", "server.key") }}
    
    - element:
        filename: additional-config.json
        template: |
          {
            "service": {
              "name": "my-service",
              "token": "{{ bitwarden_lookup("token-item-id", "fields", "service_token") }}"
            }
          }
```

#### The `bitwarden_lookup` Function

**Signature:** `bitwarden_lookup(item_id, scope, field)`

| Parameter | Description | Valid Values |
|-----------|-------------|--------------|
| `item_id` | The Bitwarden item ID | UUID string |
| `scope` | The type of field to retrieve | `login`, `fields`, `attachment` |
| `field` | The specific field name | See table below |

**Field values based on scope:**

| Scope | Valid Field Values | Description |
|-------|-------------------|-------------|
| `login` | `username`, `password` | Standard login credentials |
| `fields` | `<custom-field-name>` | Custom fields you've added in Bitwarden |
| `attachment` | `<filename>` | Name of attached file |

#### Advanced Jinja2 Features

Since templates use Jinja2, you can use control structures:

```yaml
template: |
  {% if bitwarden_lookup("item-id", "fields", "enable_feature") == "true" %}
  feature:
    enabled: true
    api_key: {{ bitwarden_lookup("item-id", "fields", "feature_api_key") }}
  {% else %}
  feature:
    enabled: false
  {% endif %}
```

#### Resulting Secret

```yaml
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: application-config
  namespace: production
  annotations:
    managed: bitwarden-template.lerentis.uploadfilter24.eu
    managedObject: default/app-config
    description: "Application configuration with secrets"
  labels:
    app: myapp
data:
  app-config.yaml: <base64-encoded-rendered-template>
  additional-config.json: <base64-encoded-rendered-template>
```

## Configuration

The operator can be configured using environment variables, either directly in `values.yaml` or via an external secret.

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BW_EMAIL` | Bitwarden account email address | - | Yes |
| `BW_PASSWORD` | Bitwarden master password | - | Yes |
| `BW_HOST` | Bitwarden server URL (for self-hosted) | `https://api.bitwarden.com/` | No |
| `BW_CLIENTID` | OAuth client ID (optional for some deployments) | - | No |
| `BW_CLIENTSECRET` | OAuth client secret (optional) | - | No |
| `BW_SYNC_INTERVAL` | How often to sync with Bitwarden (seconds) | `900` (15 min) | No |
| `BW_RELOGIN_INTERVAL` | How long to keep session unlocked / re-login interval (seconds) | `3600` (1 hour) | No |
| `BW_FORCE_SYNC` | Force sync before every secret retrieval | `false` | No |
| `DEBUG` | Enable debug logging | - | No |

### Sync Behavior

The operator interacts with the Bitwarden CLI and may perform syncs according to the configured interval:

- **Normal Mode** (`BW_FORCE_SYNC=false`): Periodic syncs based on `BW_SYNC_INTERVAL` seconds (default: 15 minutes)
- **Force Sync Mode** (`BW_FORCE_SYNC=true`): Syncs before every secret retrieval
- **Automatic Background Sync**: The Bitwarden CLI may also perform periodic syncs depending on its configuration

⚠️ **Warning:** Enabling `BW_FORCE_SYNC` can lead to rate limiting if you have many secrets or frequent updates. Use with caution.

### Session Management

The operator relies on the Bitwarden CLI for session handling:

- The CLI may keep sessions unlocked for a configured interval (`BW_RELOGIN_INTERVAL`)
- The operator assumes the CLI handles authentication state; adjust `BW_RELOGIN_INTERVAL` or credentials as needed
- No manual re-login should be required when the CLI session is valid

### Example Configuration

```yaml
# values.yaml
env:
  - name: BW_EMAIL
    value: "vault-operator@example.com"
  - name: BW_PASSWORD
    value: "your-master-password"
  # Optional: For self-hosted Bitwarden
  - name: BW_HOST
    value: "https://vault.example.com"
  - name: BW_SYNC_INTERVAL
    value: "600"  # Sync every 10 minutes
  - name: BW_RELOGIN_INTERVAL
    value: "7200"  # Keep session or re-login interval for 2 hours
  - name: DEBUG
    value: "true"  # Enable debug logging
```

## Examples

Complete working examples can be found in the repository:

- [`example.yaml`](example.yaml) - BitwardenSecret examples
- [`example_template.yaml`](example_template.yaml) - BitwardenTemplate examples  
- [`example_dockerlogin.yaml`](example_dockerlogin.yaml) - RegistryCredential examples

## Troubleshooting

### Check Operator Logs

```bash
kubectl logs -n bw-operator -l app.kubernetes.io/name=bitwarden-crd-operator -f
```

### Common Issues

**Secret not created:**
- Verify the Bitwarden item ID is correct
- Check operator logs for authentication errors
- Ensure the target namespace exists

**Authentication failures:**
- Verify `BW_EMAIL` and `BW_PASSWORD` are correct
- Check if `BW_HOST` is needed (for self-hosted instances)
- Ensure the Bitwarden CLI is installed and accessible (check logs for "Signin successful. Session exported" or "Already unlocked")

**Secrets not updating:**
- Check `BW_SYNC_INTERVAL` setting
- Verify the operator pod is running
- Look for sync errors in logs

### Garbage Collection

When you delete a `BitwardenSecret`, `RegistryCredential`, or `BitwardenTemplate` custom resource, the operator automatically deletes the associated Kubernetes Secret if it's in the same namespace (owner references are used).

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

[MIT License](LICENSE)

## Acknowledgments

Built with [kopf](https://github.com/nolar/kopf/) - Kubernetes Operators Framework
