import kopf
import kubernetes
import base64
import json

from utils.utils import unlock_bw, get_secret_from_bitwarden

def create_dockerlogin(logger, secret, secret_json, username_ref, password_ref, registry):
    secret.type = "dockerconfigjson"
    secret.data = {}
    auths_dict = {}
    registry_dict = {}
    reg_auth_dict = {}

    _username = secret_json["login"][username_ref]
    logger.info(f"Creating login with username: {_username}")
    _password = secret_json["login"][password_ref]
    cred_field = str(base64.b64encode(f"{_username}:{_password}".encode("utf-8")), "utf-8")

    reg_auth_dict["auth"] = cred_field
    registry_dict[registry] = reg_auth_dict
    auths_dict["auths"] = registry_dict
    secret.data[".dockerconfigjson"] = str(base64.b64encode(json.dumps(auths_dict).encode("utf-8")), "utf-8")
    return secret

@kopf.on.create('registry-credential.lerentis.uploadfilter24.eu')
def create_managed_registry_secret(spec, name, namespace, logger, **kwargs):
    username_ref = spec.get('usernameRef')
    password_ref = spec.get('passwordRef')
    registry = spec.get('registry')
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {id}")
    secret_json_object = json.loads(get_secret_from_bitwarden(id))

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "registry-credential.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name, annotations=annotations)
    secret = create_dockerlogin(logger, secret, secret_json_object, username_ref, password_ref, registry)   

    obj = api.create_namespaced_secret(
        secret_namespace, secret
    )

    logger.info(f"Registry Secret {secret_namespace}/{secret_name} has been created")

@kopf.on.update('registry-credential.lerentis.uploadfilter24.eu')
@kopf.timer('registry-credential.lerentis.uploadfilter24.eu', interval=900)
def update_managed_registry_secret(spec, status, name, namespace, logger, body, **kwargs):

    username_ref = spec.get('usernameRef')
    password_ref = spec.get('passwordRef')
    registry = spec.get('registry')
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')


    old_config = None
    old_secret_name = None
    old_secret_namespace = None
    if 'kopf.zalando.org/last-handled-configuration' in body.metadata.annotations:
        old_config = json.loads(body.metadata.annotations['kopf.zalando.org/last-handled-configuration'])
        old_secret_name = old_config['spec'].get('name')
        old_secret_namespace = old_config['spec'].get('namespace')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    if old_config is not None and (old_secret_name != secret_name or old_secret_namespace != secret_namespace):
        # If the name of the secret or the namespace of the secret is different
        # We have to delete the secret an recreate it
        logger.info("Secret name or namespace changed, let's recreate it")
        delete_managed_secret(old_config['spec'], name, namespace, logger, **kwargs)
        create_managed_registry_secret(spec, name, namespace, logger, **kwargs)
        return

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {id}")
    secret_json_object = json.loads(get_secret_from_bitwarden(id))

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "registry-credential.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name, annotations=annotations)
    secret = create_dockerlogin(logger, secret, secret_json_object, username_ref, password_ref, registry)
    try:
        obj = api.replace_namespaced_secret(
            name=secret_name,
            body=secret,
            namespace="{}".format(secret_namespace))
        logger.info(f"Secret {secret_namespace}/{secret_name} has been updated")
    except:
        logger.warn(
            f"Could not update secret {secret_namespace}/{secret_name}!")


@kopf.on.delete('registry-credential.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    api = kubernetes.client.CoreV1Api()

    try:
        api.delete_namespaced_secret(secret_name, secret_namespace)
        logger.info(f"Secret {secret_namespace}/{secret_name} has been deleted")
    except:
        logger.warn(f"Could not delete secret {secret_namespace}/{secret_name}!")
