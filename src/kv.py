import kopf
import kubernetes
import base64

from utils.utils import (
    get_secret_from_bitwarden, parse_login_scope, parse_fields_scope, get_attachment,
    unlock_bw, bw_sync_interval,
    build_secret_metadata, extract_secret_config, parse_old_config,
    should_recreate_secret, apply_owner_reference,
    delete_secret, create_secret, update_secret
)

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
    bw_id = spec.get('id')
    config = extract_secret_config(spec)

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {bw_id}")
    secret_json_object = get_secret_from_bitwarden(logger, bw_id)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "bitwarden-secret.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret.type = config['custom_secret_type']
    secret = create_kv(logger, bw_id, secret, secret_json_object, content_def)

    apply_owner_reference(secret, config['secret_namespace'], namespace)
    create_secret(logger, secret, config['secret_namespace'])


@kopf.on.update('bitwarden-secret.lerentis.uploadfilter24.eu')
@kopf.timer('bitwarden-secret.lerentis.uploadfilter24.eu', interval=bw_sync_interval, initial_delay=10)
def update_managed_secret(
        spec,
        status,
        name,
        namespace,
        logger,
        body,
        **kwargs):
    content_def = body['spec']['content']
    bw_id = spec.get('id')
    config = extract_secret_config(spec)
    
    old_config, old_secret_name, old_secret_namespace, old_secret_type = parse_old_config(body)

    if old_config is not None and should_recreate_secret(
            old_secret_name, config['secret_name'],
            old_secret_namespace, config['secret_namespace'],
            old_secret_type, config['custom_secret_type']):
        logger.info("Secret name, namespace or type changed, let's recreate it")
        delete_managed_secret(old_config['spec'], name, namespace, logger, **kwargs)
        create_managed_secret(spec, name, namespace, logger, body, **kwargs)
        return

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {bw_id}")
    secret_json_object = get_secret_from_bitwarden(logger, bw_id)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "bitwarden-secret.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret.type = config['custom_secret_type']
    secret = create_kv(logger, bw_id, secret, secret_json_object, content_def)

    apply_owner_reference(secret, config['secret_namespace'], namespace)
    update_secret(logger, secret, config['secret_namespace'])


@kopf.on.delete('bitwarden-secret.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    config = extract_secret_config(spec)
    delete_secret(logger, config['secret_name'], config['secret_namespace'])
