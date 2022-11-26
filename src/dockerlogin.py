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

@kopf.on.create('registry-credentials.lerentis.uploadfilter24.eu')
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
        "managed": "registry-credentials.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name, annotations=annotations)
    secret = create_dockerlogin(logger, secret, secret_json_object, username_ref, password_ref, registry)   

    obj = api.create_namespaced_secret(
        secret_namespace, secret
    )

    logger.info(f"Registry Secret {secret_namespace}/{secret_name} has been created")

@kopf.on.update('registry-credentials.lerentis.uploadfilter24.eu')
def my_handler(spec, old, new, diff, **_):
    pass

@kopf.on.delete('registry-credentials.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    api = kubernetes.client.CoreV1Api()

    try:
        api.delete_namespaced_secret(secret_name, secret_namespace)
        logger.info(f"Secret {secret_namespace}/{secret_name} has been deleted")
    except:
        logger.warn(f"Could not delete secret {secret_namespace}/{secret_name}!")
