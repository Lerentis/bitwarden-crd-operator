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
        "bitwarden_lookup_with_name": BitwardenLookupHandler(logger).bitwarden_lookup_with_name,
    })
    return jinja_template.render()


def create_template_secret(logger, spec, body, **kwargs):
    template = spec.get('template')
    filename = spec.get('filename')
    secret_name = spec.get('name')
    labels = spec.get('labels')

    annotations = {
        "managed": "bitwarden-template.lerentis.uploadfilter24.eu",
        "managedObject": f"{body.get('metadata').get('namespace')}/{body.get('metadata').get('name')}"
    }

    if not labels:
        labels = {}

    owner_references = [{
        "apiVersion": f"{body.get('apiVersion')}",
        "blockOwnerDeletion": True,
        "controller": True,
        "kind": f"{body.get('kind')}",
        "name": f"{body.get('metadata').get('name')}",
        "uid": f"{body.get('metadata').get('uid')}",
    }]

    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name,
        annotations=annotations, labels=labels, owner_references=owner_references)

    secret.type = "Opaque"
    secret.data = {}
    secret.data[filename] = str(
        base64.b64encode(
            render_template(logger, template).encode("utf-8")),
        "utf-8")
    return secret


@kopf.on.create('bitwarden-template.lerentis.uploadfilter24.eu')
def create_managed_secret(spec, name, namespace, logger, body, **kwargs):
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    unlock_bw(logger)
    secret = create_template_secret(logger, spec, body, **kwargs)
    api = kubernetes.client.CoreV1Api()
    api.create_namespaced_secret(secret_namespace, secret)

    try:
        api = kubernetes.client.CoreV1Api()
        api.create_namespaced_secret(secret_namespace, secret)
        logger.info(f"Secret {secret_namespace}/{secret_name} has been created")
    except BaseException as e:
        logger.info(e)
        logger.warn(
            f"Could not create secret '{secret_namespace}/{secret_name}!")


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
    filename = spec.get('filename')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    labels = spec.get('labels')

    old_config = None
    old_secret_name = None
    old_secret_namespace = None
    if 'kopf.zalando.org/last-handled-configuration' in body.metadata.annotations:
        old_config = json.loads(
            body.metadata.annotations['kopf.zalando.org/last-handled-configuration'])
        old_secret_name = old_config['spec'].get('name')
        old_secret_namespace = old_config['spec'].get('namespace')

    if old_config is not None and (
            old_secret_name != secret_name or old_secret_namespace != secret_namespace):
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
    secret = create_template_secret(logger, spec, body, **kwargs)

    try:
        api = kubernetes.client.CoreV1Api()
        api.replace_namespaced_secret(
            name=secret_name,
            body=secret,
            namespace="{}".format(secret_namespace))
        logger.info(
            f"Secret {secret_namespace}/{secret_name} has been updated")
    except BaseException:
        logger.warn(
            f"Could not update secret {secret_namespace}/{secret_name}!")


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
