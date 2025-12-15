import kopf
import base64
import kubernetes

from utils.utils import (
    get_secret_from_bitwarden, parse_login_scope, parse_fields_scope, get_attachment,
    unlock_bw, bw_sync_interval,
    build_secret_metadata, extract_secret_config, parse_old_config,
    should_recreate_secret, apply_owner_reference,
    delete_secret, create_secret, update_secret
)
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
        return
        
    content_def = spec.get('content')
    config = extract_secret_config(spec)

    unlock_bw(logger)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "bitwarden-template.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret.type = config['custom_secret_type']
    secret = create_template_obj(logger, secret, content_def)

    apply_owner_reference(secret, config['secret_namespace'], namespace)
    create_secret(logger, secret, config['secret_namespace'])


def create_beta7_secret(spec, name, namespace, logger, body, **kwargs):
    template = spec.get('template')
    filename = spec.get('filename')
    config = extract_secret_config(spec)

    unlock_bw(logger)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "bitwarden-template.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret.type = config['custom_secret_type']
    secret = create_template_secret(logger, secret, filename, template)

    apply_owner_reference(secret, config['secret_namespace'], namespace)
    create_secret(logger, secret, config['secret_namespace'])

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
    config = extract_secret_config(spec)

    old_config, old_secret_name, old_secret_namespace, old_secret_type = parse_old_config(body)

    if old_config is not None and should_recreate_secret(
            old_secret_name, config['secret_name'],
            old_secret_namespace, config['secret_namespace'],
            old_secret_type, config['custom_secret_type']):
        logger.info("Secret name or namespace changed, let's recreate it")
        delete_managed_secret(old_config['spec'], name, namespace, logger, **kwargs)
        create_managed_secret(spec, name, namespace, logger, body, **kwargs)
        return

    unlock_bw(logger)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "bitwarden-template.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret.type = config['custom_secret_type']
    secret = create_template_secret(logger, secret, filename, template)

    apply_owner_reference(secret, config['secret_namespace'], namespace)
    update_secret(logger, secret, config['secret_namespace'])



@kopf.on.update('bitwarden-template.lerentis.uploadfilter24.eu')
@kopf.timer('bitwarden.lerentis.uploadfilter24.eu', 'bitwardentemplate', interval=bw_sync_interval, initial_delay=10)
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
        return
        
    content_def = spec.get('content')
    config = extract_secret_config(spec)

    old_config, old_secret_name, old_secret_namespace, old_secret_type = parse_old_config(body)

    if old_config is not None and should_recreate_secret(
            old_secret_name, config['secret_name'],
            old_secret_namespace, config['secret_namespace'],
            old_secret_type, config['custom_secret_type']):
        logger.info("Secret name or namespace changed, let's recreate it")
        delete_managed_secret(old_config['spec'], name, namespace, logger, **kwargs)
        create_managed_secret(spec, name, namespace, logger, body, **kwargs)
        return

    unlock_bw(logger)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "bitwarden-template.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret.type = config['custom_secret_type']
    secret = create_template_obj(logger, secret, content_def)

    apply_owner_reference(secret, config['secret_namespace'], namespace)
    update_secret(logger, secret, config['secret_namespace'])


@kopf.on.delete('bitwarden-template.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    config = extract_secret_config(spec)
    delete_secret(logger, config['secret_name'], config['secret_namespace'])
