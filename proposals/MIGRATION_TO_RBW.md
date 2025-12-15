# Migration to rbw

This document describes the migration from the official Bitwarden CLI to rbw (Rust Bitwarden CLI).

## Why rbw?

[rbw](https://github.com/doy/rbw) is an unofficial command line client for Bitwarden that offers several advantages over the official CLI:

### Benefits

1. **Stateful Agent** - rbw maintains a background agent (`rbw-agent`) that keeps the vault unlocked, eliminating the need to pass session tokens around in environment variables
2. **Better Security** - No session tokens stored in environment variables; the agent manages authentication state securely
3. **Simpler API** - Direct JSON output without wrapper response objects
4. **Automatic Sync** - The agent can perform background syncs automatically
5. **No Re-login Required** - Unlike the official CLI where sessions expire, rbw's agent handles authentication persistently
6. **Rust Performance** - Written in Rust for better performance and memory safety

### Trade-offs

- Less widely adopted than the official CLI
- Requires the rbw agent to be running (handled automatically by the operator)
- Slightly different command syntax
- Login requires TTY (needs to be worked around by the operator somehow)

## What Changed

### Authentication

**Before (Official CLI with API Keys):**
```yaml
env:
  - name: BW_HOST
    value: "https://bitwarden.example.com"
  - name: BW_CLIENTID
    value: "user.client-id"
  - name: BW_CLIENTSECRET
    value: "client-secret"
  - name: BW_PASSWORD
    value: "master-password"
```

**After (rbw with Email):**
```yaml
env:
  - name: RBW_EMAIL
    value: "user@example.com"
  - name: RBW_PASSWORD
    value: "master-password"
  - name: RBW_BASE_URL  # Optional, for self-hosted
    value: "https://bitwarden.example.com"
```

### Configuration

| Old Variable | New Variable | Notes |
|-------------|-------------|-------|
| `BW_HOST` | `RBW_BASE_URL` | Server URL for self-hosted instances |
| `BW_CLIENTID` | `RBW_EMAIL` | Now uses email instead of API client ID |
| `BW_CLIENTSECRET` | _(removed)_ | No longer needed |
| `BW_PASSWORD` | `RBW_PASSWORD` | Same purpose |
| `BW_SYNC_INTERVAL` | `RBW_SYNC_INTERVAL` | Same purpose |
| `BW_RELOGIN_INTERVAL` | `RBW_LOCK_TIMEOUT` | Changed from re-login interval to lock timeout |
| `BW_FORCE_SYNC` | `RBW_FORCE_SYNC` | Same purpose |

### Code Changes

#### Command Execution

**Before:**
```python
# Official CLI wraps output in response object
command_wrapper(logger, "get item {id}")
# Returns: {"success": true, "data": {...}}
```

**After:**
```python
# rbw returns direct JSON output
command_wrapper(logger, "get --full {id}")
# Returns: {...item data...}
```

#### Authentication Flow

**Before:**
```python
def bitwarden_signin(logger):
    command_wrapper(logger, "config server {url}")
    command_wrapper(logger, "login --apikey")
    unlock_bw(logger)
```

**After:**
```python
def rbw_configure(logger):
    command_wrapper(logger, "config set email {email}")
    command_wrapper(logger, "config set base_url {url}")
    unlock_rbw(logger)
```

#### Unlocking

**Before:**
```python
# Required session token management
token_output = command_wrapper(logger, "unlock --passwordenv BW_PASSWORD")
os.environ["BW_SESSION"] = token_output["data"]["raw"]
```

**After:**
```python
# Agent-based unlocking with stdin password
password = os.environ.get('RBW_PASSWORD')
command_with_input(logger, "unlock", password)
# Agent maintains unlocked state
```

### File Changes

The following files need to be modified:

1. **`src/utils/utils.py`** - Complete refactor of command wrapper and authentication
2. **`src/bitwardenCrdOperator.py`** - Updated startup and configuration logic
3. **`src/kv.py`** - Updated to use rbw functions
4. **`src/dockerlogin.py`** - Updated to use rbw functions
5. **`src/template.py`** - Updated to use rbw functions
6. **`README.md`** - Updated documentation for rbw
7. **`Dockerfile`** - Already includes rbw

### Function Renames

| Old Function | New Function |
|-------------|-------------|
| `unlock_bw()` | `unlock_rbw()` |
| `sync_bw()` | `sync_rbw()` |
| `bitwarden_signin()` | `rbw_configure()` + `rbw_login_and_unlock()` |
| `bw_sync_interval` | `rbw_sync_interval` |
| `BitwardenCommandException` | `RbwCommandException` |

## Migration Checklist

If you're upgrading from the old version:

- [ ] Update environment variables from `BW_*` to `RBW_*`
- [ ] Replace `BW_CLIENTID` and `BW_CLIENTSECRET` with `RBW_EMAIL`
- [ ] Update `BW_HOST` to `RBW_BASE_URL` (if using self-hosted)
- [ ] Remove `BW_RELOGIN_INTERVAL` (no longer needed)
- [ ] Add `RBW_LOCK_TIMEOUT` if you want to customize unlock duration
- [ ] Update any documentation or deployment scripts
- [ ] Test authentication with new credentials

## Compatibility

- **Kubernetes**: No changes required in CRD definitions
- **Secrets**: Generated secrets remain identical
- **API**: All BitwardenSecret, RegistryCredential, and BitwardenTemplate CRDs work exactly the same

## Troubleshooting

### rbw not unlocking

**Error:** "RBW_PASSWORD environment variable not set"
**Solution:** Ensure `RBW_PASSWORD` is set in your environment variables or secret

### Agent not starting

**Error:** "Could not connect to rbw-agent"
**Solution:** The operator automatically starts the agent. Check logs for agent startup errors.

### Authentication failures

**Error:** "Invalid email or password"
**Solution:** 
1. Verify `RBW_EMAIL` matches your Bitwarden account
2. Verify `RBW_PASSWORD` is correct
3. For self-hosted, ensure `RBW_BASE_URL` is correctly set

**Error:** "Invalid email or password"

```text
rbw unlock: failed to read password from pinentry: failed to parse pinentry output (\"S ERROR curses.isatty 83918950 \\nERR 83918950 Not a tty
```
**Solution**
None yet

### Sync issues

**Error:** "Sync failed"
**Solution:**
1. Check network connectivity to Bitwarden server
2. Verify `RBW_BASE_URL` is correct (for self-hosted)
3. Check if the vault is locked (unlock automatically retries)

## Resources

- [rbw GitHub Repository](https://github.com/doy/rbw)
- [rbw Documentation](https://github.com/doy/rbw/blob/master/README.md)
- [Bitwarden CLI Comparison](https://github.com/doy/rbw#motivation)
