import kopf
import kubernetes
import base64
import json

from utils.utils import unlock_bw, get_secret_from_bitwarden, parse_login_scope, parse_fields_scope


def create_kv(secret, secret_json, content_def):
    secret.type = "Opaque"
    secret.data = {}
    for eleml in content_def:
        for k, elem in eleml.items():
            for key, value in elem.items():
                if key == "secretName":
                    _secret_key = value
                if key == "secretRef":
                    _secret_ref = value
                if key == "secretScope":
                    _secret_scope = value
            if _secret_scope == "login":
                secret.data[_secret_ref] = str(base64.b64encode(
                    parse_login_scope(secret_json, _secret_key).encode("utf-8")), "utf-8")
            if _secret_scope == "fields":
                secret.data[_secret_ref] = str(base64.b64encode(
                    parse_fields_scope(secret_json, _secret_key).encode("utf-8")), "utf-8")
    return secret


@kopf.on.create('bitwarden-secret.lerentis.uploadfilter24.eu')
def create_managed_secret(spec, name, namespace, logger, body, **kwargs):

    content_def = body['spec']['content']
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {id}")
    secret_json_object = json.loads(get_secret_from_bitwarden(id))

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-secret.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(
        name=secret_name, annotations=annotations)
    secret = create_kv(secret, secret_json_object, content_def)

    obj = api.create_namespaced_secret(
        namespace="{}".format(secret_namespace),
        body=secret
    )

    logger.info(f"Secret {secret_namespace}/{secret_name} has been created")


@kopf.on.update('bitwarden-secret.lerentis.uploadfilter24.eu')
@kopf.timer('bitwarden-secret.lerentis.uploadfilter24.eu', interval=900)
def update_managed_secret(spec, status, name, namespace, logger, body, **kwargs):

    content_def = body['spec']['content']
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {id}")
    secret_json_object = json.loads(get_secret_from_bitwarden(id))

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-secret.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }

    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(
        name=secret_name, annotations=annotations)
    secret = create_kv(secret, secret_json_object, content_def)

    try:
        obj = api.replace_namespaced_secret(
            name=secret_name,
            body=secret,
            namespace="{}".format(secret_namespace))
        logger.info(f"Secret {secret_namespace}/{secret_name} has been updated")
    except:
        logger.warn(
            f"Could not update secret {secret_namespace}/{secret_name}!")


@kopf.on.delete('bitwarden-secret.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    api = kubernetes.client.CoreV1Api()

    try:
        api.delete_namespaced_secret(secret_name, secret_namespace)
        logger.info(
            f"Secret {secret_namespace}/{secret_name} has been deleted")
    except:
        logger.warn(
            f"Could not delete secret {secret_namespace}/{secret_name}!")
