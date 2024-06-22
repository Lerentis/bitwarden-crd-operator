import kopf
import kubernetes
import base64
import json

from utils.utils import unlock_bw, get_secret_from_bitwarden, parse_login_scope, parse_fields_scope, get_attachment, bw_sync_interval

def create_kv(logger, id, secret, secret_json, content_def):
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
                value = parse_login_scope(secret_json, _secret_key)
                if value is None:
                    raise Exception(
                        f"Field {_secret_key} has no value in bitwarden secret")
                secret.data[_secret_ref] = str(base64.b64encode(
                    value.encode("utf-8")), "utf-8")
            if _secret_scope == "fields":
                value = parse_fields_scope(secret_json, _secret_key)
                if value is None:
                    raise Exception(
                        f"Field {_secret_key} has no value in bitwarden secret")
                secret.data[_secret_ref] = str(base64.b64encode(
                    value.encode("utf-8")), "utf-8")
            if _secret_scope == "attachment":
                value = get_attachment(logger, id, _secret_key)
                if value is None:
                    raise Exception(
                        f"Attachment {_secret_key} has no value in bitwarden secret")
                secret.data[_secret_ref] = str(base64.b64encode(
                    value.encode("utf-8")), "utf-8")
    return secret


@kopf.on.create('bitwarden-secret.lerentis.uploadfilter24.eu')
def create_managed_secret(spec, name, namespace, logger, body, **kwargs):

    content_def = body['spec']['content']
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    labels = spec.get('labels')
    custom_annotations = spec.get('annotations')
    custom_secret_type = spec.get('secretType')

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {id}")
    secret_json_object = get_secret_from_bitwarden(logger, id)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-secret.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }

    if custom_annotations:
        annotations.update(custom_annotations)

    if not custom_secret_type:
        custom_secret_type = 'Opaque'

    if not labels:
        labels = {}

    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(
        name=secret_name, annotations=annotations, labels=labels)
    secret.type = custom_secret_type
    secret = create_kv(logger, id, secret, secret_json_object, content_def)

    # Garbage collection will delete the generated secret if the owner
    # Is not in the same namespace as the generated secret
    if secret_namespace == namespace:
        kopf.append_owner_reference(secret)

    api.create_namespaced_secret(
        namespace="{}".format(secret_namespace),
        body=secret
    )

    logger.info(f"Secret {secret_namespace}/{secret_name} has been created")


@kopf.on.update('bitwarden-secret.lerentis.uploadfilter24.eu')
@kopf.timer('bitwarden-secret.lerentis.uploadfilter24.eu', interval=bw_sync_interval)
def update_managed_secret(
        spec,
        status,
        name,
        namespace,
        logger,
        body,
        **kwargs):

    content_def = body['spec']['content']
    id = spec.get('id')
    old_config = None
    old_secret_name = None
    old_secret_namespace = None
    old_secret_type = None
    if 'kopf.zalando.org/last-handled-configuration' in body.metadata.annotations:
        old_config = json.loads(
            body.metadata.annotations['kopf.zalando.org/last-handled-configuration'])
        old_secret_name = old_config['spec'].get('name')
        old_secret_namespace = old_config['spec'].get('namespace')
        old_secret_type = old_config['spec'].get('type')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    labels = spec.get('labels')
    custom_annotations = spec.get('annotations')
    custom_secret_type = spec.get('secretType')

    if not custom_secret_type:
        custom_secret_type = 'Opaque'

    if old_config is not None and (
            old_secret_name != secret_name or old_secret_namespace != secret_namespace or old_secret_type != custom_secret_type):
        # If the name of the secret or the namespace of the secret is different
        # We have to delete the secret an recreate it
        logger.info("Secret name, namespace or type changed, let's recreate it")
        delete_managed_secret(
            old_config['spec'],
            name,
            namespace,
            logger,
            **kwargs)
        create_managed_secret(spec, name, namespace, logger, body, **kwargs)
        return

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {id}")
    secret_json_object = get_secret_from_bitwarden(logger, id)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-secret.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }

    if custom_annotations:
        annotations.update(custom_annotations)

    if not labels:
        labels = {}

    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(
        name=secret_name, annotations=annotations, labels=labels)
    secret.type = custom_secret_type
    secret = create_kv(logger, id, secret, secret_json_object, content_def)

    # Garbage collection will delete the generated secret if the owner
    # Is not in the same namespace as the generated secret
    if secret_namespace == namespace:
        kopf.append_owner_reference(secret)

    try:
        api.replace_namespaced_secret(
            name=secret_name,
            body=secret,
            namespace="{}".format(secret_namespace))
        logger.info(
            f"Secret {secret_namespace}/{secret_name} has been updated")
    except BaseException as e:
        logger.warn(
            f"Could not update secret {secret_namespace}/{secret_name}!")
        logger.warn(
            f"Exception: {e}"
        )


@kopf.on.delete('bitwarden-secret.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    api = kubernetes.client.CoreV1Api()

    try:
        api.delete_namespaced_secret(secret_name, secret_namespace)
        logger.info(
            f"Secret {secret_namespace}/{secret_name} has been deleted")
    except BaseException:
        logger.warn(
            f"Could not delete secret {secret_namespace}/{secret_name}!")
