import kopf
import base64
import kubernetes
import json

from utils.utils import unlock_bw
from lookups.bitwarden_lookup import bitwarden_lookup
from jinja2 import Environment, BaseLoader


lookup_func_dict = {
    "bitwarden_lookup": bitwarden_lookup,
}

def render_template(template):
    jinja_template = Environment(loader=BaseLoader()).from_string(template)
    jinja_template.globals.update(lookup_func_dict)
    return jinja_template.render()

def create_template_secret(secret, filename, template):
    secret.type = "Opaque"
    secret.data = {}
    secret.data[filename] = str(base64.b64encode(render_template(template).encode("utf-8")), "utf-8")
    return secret

@kopf.on.create('bitwarden-template.lerentis.uploadfilter24.eu')
def create_managed_secret(spec, name, namespace, logger, body, **kwargs):

    template = spec.get('template')
    filename = spec.get('filename')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    unlock_bw(logger)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-template.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name, annotations=annotations)
    secret = create_template_secret(secret, filename, template)

    obj = api.create_namespaced_secret(
        secret_namespace, secret
    )

    logger.info(f"Secret {secret_namespace}/{secret_name} has been created")

@kopf.on.update('bitwarden-template.lerentis.uploadfilter24.eu')
@kopf.timer('bitwarden-template.lerentis.uploadfilter24.eu', interval=900)
def update_managed_secret(spec, status, name, namespace, logger, body, **kwargs):

    template = spec.get('template')
    filename = spec.get('filename')
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
        create_managed_secret(spec, name, namespace, logger, body, **kwargs)
        return

    unlock_bw(logger)

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-template.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name, annotations=annotations)
    secret = create_template_secret(secret, filename, template)

    try:
        obj = api.replace_namespaced_secret(
            name=secret_name,
            body=secret,
            namespace="{}".format(secret_namespace))
        logger.info(f"Secret {secret_namespace}/{secret_name} has been updated")
    except:
        logger.warn(
            f"Could not update secret {secret_namespace}/{secret_name}!")

@kopf.on.delete('bitwarden-template.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    api = kubernetes.client.CoreV1Api()

    try:
        api.delete_namespaced_secret(secret_name, secret_namespace)
        logger.info(f"Secret {secret_namespace}/{secret_name} has been deleted")
    except:
        logger.warn(f"Could not delete secret {secret_namespace}/{secret_name}!")
