import kopf
import base64
import kubernetes
import json

from utils.utils import unlock_bw, bw_sync_interval
from lookups.bitwarden_lookup import BitwardenLookupHandler
from jinja2 import Environment, BaseLoader


def render_template(logger, template):
    jinja_template = Environment(loader=BaseLoader()).from_string(template)
    jinja_template.globals.update({
        "bitwarden_lookup": BitwardenLookupHandler(logger).bitwarden_lookup,
    })
    return jinja_template.render()


def create_template_secret(logger, secret, filename, template):
    secret.data = {}
    secret.data[filename] = str(
        base64.b64encode(
            render_template(logger, template).encode("utf-8")),
        "utf-8")
    return secret

def create_template_obj(logger, secret, content_def):
    secret.data = {}
    for eleml in content_def:
        for k, elem in eleml.items():
            for key, value in elem.items():
                if key == "filename":
                    _file_name = value
                if key == "template":
                    _template = value
            secret.data[_file_name] = str(
                base64.b64encode(
                    render_template(logger, _template).encode("utf-8")),
                "utf-8")
    return secret


@kopf.on.create('bitwarden-template.lerentis.uploadfilter24.eu')
def create_managed_secret(spec, name, namespace, logger, body, **kwargs):
    template = spec.get('template')
    if template is not None:
        create_beta7_secret(spec, name, namespace, logger, body, **kwargs)
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    custom_secret_type = spec.get('secretType')
    labels = spec.get('labels')
    custom_annotations = spec.get('annotations')
    content_def = spec.get('content')

    unlock_bw(logger)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-template.lerentis.uploadfilter24.eu",
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
    secret = create_template_obj(logger, secret, content_def)

    # Garbage collection will delete the generated secret if the owner
    # Is not in the same namespace as the generated secret
    if secret_namespace == namespace:
        kopf.append_owner_reference(secret)
    
    api.create_namespaced_secret(
        namespace="{}".format(secret_namespace),
        body=secret
    )

    logger.info(f"Secret {secret_namespace}/{secret_name} has been created")


def create_beta7_secret(spec, name, namespace, logger, body, **kwargs):

    template = spec.get('template')
    filename = spec.get('filename')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    labels = spec.get('labels')
    custom_annotations = spec.get('annotations')
    custom_secret_type = spec.get('secretType')

    unlock_bw(logger)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-template.lerentis.uploadfilter24.eu",
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
    secret = create_template_secret(logger, secret, filename, template)

    # Garbage collection will delete the generated secret if the owner
    # Is not in the same namespace as the generated secret
    if secret_namespace == namespace:
        kopf.append_owner_reference(secret)

    api.create_namespaced_secret(
        secret_namespace, secret
    )

    logger.info(f"Secret {secret_namespace}/{secret_name} has been created")

def update_beta7_secret(
        spec,
        status,
        name,
        namespace,
        logger,
        body,
        **kwargs):

    template = spec.get('template')
    filename = spec.get('filename')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    labels = spec.get('labels')
    custom_annotations = spec.get('annotations')
    custom_secret_type = spec.get('secretType')

    if not custom_secret_type:
        custom_secret_type = 'Opaque'

    old_config = None
    old_secret_name = None
    old_secret_namespace = None
    old_secret_type = None
    if 'kopf.zalando.org/last-handled-configuration' in body.metadata.annotations:
        old_config = json.loads(
            body.metadata.annotations['kopf.zalando.org/last-handled-configuration'])
        old_secret_name = old_config['spec'].get('name')
        old_secret_namespace = old_config['spec'].get('namespace')
        old_secret_type = old_config['spec'].get('secretType')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    if not old_secret_type:
      old_secret_type = 'Opaque'

    if old_config is not None and (
            old_secret_name != secret_name or old_secret_namespace != secret_namespace or old_secret_type != custom_secret_type):
        # If the name of the secret or the namespace of the secret is different
        # We have to delete the secret an recreate it
        logger.info("Secret name or namespace changed, let's recreate it")
        delete_managed_secret(
            old_config['spec'],
            name,
            namespace,
            logger,
            **kwargs)
        create_managed_secret(spec, name, namespace, logger, body, **kwargs)
        return

    unlock_bw(logger)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-template.lerentis.uploadfilter24.eu",
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
    secret = create_template_secret(logger, secret, filename, template)

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



@kopf.on.update('bitwarden-template.lerentis.uploadfilter24.eu')
@kopf.timer('bitwarden-template.lerentis.uploadfilter24.eu', interval=bw_sync_interval)
def update_managed_secret(
        spec,
        status,
        name,
        namespace,
        logger,
        body,
        **kwargs):

    template = spec.get('template')
    if template is not None:
        update_beta7_secret(spec, status, name, namespace, logger, body, **kwargs)
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    labels = spec.get('labels')
    custom_annotations = spec.get('annotations')
    custom_secret_type = spec.get('secretType')
    content_def = spec.get('content')

    if not custom_secret_type:
        custom_secret_type = 'Opaque'

    old_config = None
    old_secret_name = None
    old_secret_namespace = None
    old_secret_type = None
    if 'kopf.zalando.org/last-handled-configuration' in body.metadata.annotations:
        old_config = json.loads(
            body.metadata.annotations['kopf.zalando.org/last-handled-configuration'])
        old_secret_name = old_config['spec'].get('name')
        old_secret_namespace = old_config['spec'].get('namespace')
        old_secret_type = old_config['spec'].get('secretType')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    if not old_secret_type:
      old_secret_type = 'Opaque'

    if old_config is not None and (
            old_secret_name != secret_name or old_secret_namespace != secret_namespace or old_secret_type != custom_secret_type):
        # If the name of the secret or the namespace of the secret is different
        # We have to delete the secret an recreate it
        logger.info("Secret name or namespace changed, let's recreate it")
        delete_managed_secret(
            old_config['spec'],
            name,
            namespace,
            logger,
            **kwargs)
        create_managed_secret(spec, name, namespace, logger, body, **kwargs)
        return

    unlock_bw(logger)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-template.lerentis.uploadfilter24.eu",
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
    secret = create_template_obj(logger, secret, content_def)

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


@kopf.on.delete('bitwarden-template.lerentis.uploadfilter24.eu')
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
