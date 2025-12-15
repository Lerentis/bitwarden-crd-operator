import os
import json
import subprocess
import distutils
import kubernetes
import kopf

bw_sync_interval = float(os.environ.get(
    'BW_SYNC_INTERVAL', 900))

class BitwardenCommandException(Exception):
    pass


def get_secret_from_bitwarden(logger, id, force_sync=False):
    sync_bw(logger, force=force_sync)
    return command_wrapper(logger, command=f"get item {id}")


def sync_bw(logger, force=False):
    def _sync(logger):
        status = command_wrapper(logger, command=f"sync")
        if status is None:
            logger.info(f"Sync failed, retrying in {bw_sync_interval} seconds")
        return

    if force:
        _sync(logger)
        if "DEBUG" in dict(os.environ):
            logger.info("Running with regular force sync enabled")
        return

    global_force_sync = bool(distutils.util.strtobool(
        os.environ.get('BW_FORCE_SYNC', "false")))

    if global_force_sync:
        _sync(logger)
        if "DEBUG" in dict(os.environ):
            logger.info("Running with global force sync")
    else:
        _sync(logger)


def get_attachment(logger, id, name):
    return command_wrapper(logger, command=f"get attachment {name} --itemid {id}", raw=True)


def unlock_bw(logger):
    status_output = command_wrapper(logger, "status", False)
    status = status_output['data']['template']['status']
    if status == 'unlocked':
        if "DEBUG" in dict(os.environ):
            logger.info("Already unlocked")
        return
    token_output = command_wrapper(logger, "unlock --passwordenv BW_PASSWORD")
    os.environ["BW_SESSION"] = token_output["data"]["raw"]
    logger.info("Signin successful. Session exported")


def command_wrapper(logger, command, use_success: bool = True, raw: bool = False):
    system_env = dict(os.environ)
    response_flag = "--raw" if raw else "--response"
    sp = subprocess.Popen(
        [f"bw {response_flag} {command}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        shell=True,
        env=system_env)
    out, err = sp.communicate()
    if err:
        logger.warn(err)
        return None
    if raw:
        return out.decode(encoding='UTF-8')
    if "DEBUG" in system_env:
        logger.info(out.decode(encoding='UTF-8'))
    resp = json.loads(out.decode(encoding='UTF-8'))
    if resp["success"] != None and (not use_success or (use_success and resp["success"] == True)):
        return resp
    logger.warn(resp)
    return None


def parse_login_scope(secret_json, key):
    return secret_json["data"]["login"][key]


def parse_fields_scope(secret_json, key):
    if "fields" not in secret_json["data"]:
        return None
    for entry in secret_json["data"]["fields"]:
        if entry['name'] == key:
            return entry['value']


# Common secret management functions
def build_secret_metadata(secret_name, managed_type, namespace, name, custom_annotations=None, labels=None):
    """Build common secret metadata with annotations and labels."""
    annotations = {
        "managed": managed_type,
        "managedObject": f"{namespace}/{name}"
    }
    
    if custom_annotations:
        annotations.update(custom_annotations)
    
    if not labels:
        labels = {}
    
    return kubernetes.client.V1ObjectMeta(
        name=secret_name, 
        annotations=annotations, 
        labels=labels
    )


def extract_secret_config(spec):
    """Extract common secret configuration from spec."""
    return {
        'secret_name': spec.get('name'),
        'secret_namespace': spec.get('namespace'),
        'labels': spec.get('labels'),
        'custom_annotations': spec.get('annotations'),
        'custom_secret_type': spec.get('secretType', 'Opaque')
    }


def parse_old_config(body):
    """Parse old configuration from body annotations."""
    if 'kopf.zalando.org/last-handled-configuration' not in body.metadata.annotations:
        return None, None, None, None
    
    old_config = json.loads(
        body.metadata.annotations['kopf.zalando.org/last-handled-configuration']
    )
    old_secret_name = old_config['spec'].get('name')
    old_secret_namespace = old_config['spec'].get('namespace')
    old_secret_type = old_config['spec'].get('secretType', 'Opaque')
    
    return old_config, old_secret_name, old_secret_namespace, old_secret_type


def should_recreate_secret(old_secret_name, secret_name, old_secret_namespace, 
                           secret_namespace, old_secret_type, secret_type):
    """Determine if secret should be recreated due to name/namespace/type change."""
    return (old_secret_name != secret_name or 
            old_secret_namespace != secret_namespace or 
            old_secret_type != secret_type)


def apply_owner_reference(secret, secret_namespace, namespace):
    """Apply owner reference if secret is in same namespace."""
    if secret_namespace == namespace:
        kopf.append_owner_reference(secret)


def delete_secret(logger, secret_name, secret_namespace):
    """Delete a Kubernetes secret."""
    api = kubernetes.client.CoreV1Api()
    
    try:
        api.delete_namespaced_secret(secret_name, secret_namespace)
        logger.info(f"Secret {secret_namespace}/{secret_name} has been deleted")
    except BaseException:
        logger.warn(f"Could not delete secret {secret_namespace}/{secret_name}!")


def create_secret(logger, secret, secret_namespace):
    """Create a Kubernetes secret."""
    api = kubernetes.client.CoreV1Api()
    api.create_namespaced_secret(
        namespace=secret_namespace,
        body=secret
    )
    logger.info(f"Secret {secret_namespace}/{secret.metadata.name} has been created")


def update_secret(logger, secret, secret_namespace):
    """Update a Kubernetes secret."""
    api = kubernetes.client.CoreV1Api()
    
    try:
        api.replace_namespaced_secret(
            name=secret.metadata.name,
            body=secret,
            namespace=secret_namespace
        )
        logger.info(f"Secret {secret_namespace}/{secret.metadata.name} has been updated")
    except BaseException as e:
        logger.warn(f"Could not update secret {secret_namespace}/{secret.metadata.name}!")
        logger.warn(f"Exception: {e}")
