import kopf
import kubernetes
import base64
import json

from utils.utils import (
    get_secret_from_bitwarden,
    unlock_bw, bw_sync_interval,
    build_secret_metadata, extract_secret_config, parse_old_config,
    should_recreate_secret, apply_owner_reference,
    delete_secret, create_secret, update_secret
)


def create_dockerlogin(
        logger,
        secret,
        secret_json,
        username_ref,
        password_ref,
        registry):
    secret.type = "kubernetes.io/dockerconfigjson"
    secret.data = {}
    auths_dict = {}
    registry_dict = {}
    reg_auth_dict = {}

    _username = secret_json["login"][username_ref]
    logger.info(f"Creating login with username: {_username}")
    _password = secret_json["login"][password_ref]
    cred_field = str(
        base64.b64encode(
            f"{_username}:{_password}".encode("utf-8")),
        "utf-8")
    reg_auth_dict["username"] = _username
    reg_auth_dict["password"] = _password
    reg_auth_dict["auth"] = cred_field
    registry_dict[registry] = reg_auth_dict
    auths_dict["auths"] = registry_dict
    secret.data[".dockerconfigjson"] = str(base64.b64encode(
        json.dumps(auths_dict).encode("utf-8")), "utf-8")
    return secret


@kopf.on.create('registry-credential.lerentis.uploadfilter24.eu')
def create_managed_registry_secret(spec, name, namespace, logger, **kwargs):
    username_ref = spec.get('usernameRef')
    password_ref = spec.get('passwordRef')
    registry = spec.get('registry')
    bw_id = spec.get('id')
    config = extract_secret_config(spec)

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {bw_id}")
    secret_json_object = get_secret_from_bitwarden(logger, bw_id)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "registry-credential.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret = create_dockerlogin(
        logger,
        secret,
        secret_json_object["data"],
        username_ref,
        password_ref,
        registry)
    
    apply_owner_reference(secret, config['secret_namespace'], namespace)
    create_secret(logger, secret, config['secret_namespace'])


@kopf.on.update('registry-credential.lerentis.uploadfilter24.eu')
@kopf.timer('bitwarden.lerentis.uploadfilter24.eu', 'registrycredential', interval=bw_sync_interval, initial_delay=10)
def update_managed_registry_secret(
        spec,
        status,
        name,
        namespace,
        logger,
        body,
        **kwargs):
    username_ref = spec.get('usernameRef')
    password_ref = spec.get('passwordRef')
    registry = spec.get('registry')
    bw_id = spec.get('id')
    config = extract_secret_config(spec)

    old_config, old_secret_name, old_secret_namespace, old_secret_type = parse_old_config(body)

    if old_config is not None and should_recreate_secret(
            old_secret_name, config['secret_name'],
            old_secret_namespace, config['secret_namespace'],
            old_secret_type, config['custom_secret_type']):
        logger.info("Secret name or namespace changed, let's recreate it")
        delete_managed_secret(old_config['spec'], name, namespace, logger, **kwargs)
        create_managed_registry_secret(spec, name, namespace, logger, **kwargs)
        return

    unlock_bw(logger)
    logger.info(f"Locking up secret with ID: {bw_id}")
    secret_json_object = get_secret_from_bitwarden(logger, bw_id)

    secret = kubernetes.client.V1Secret()
    secret.metadata = build_secret_metadata(
        config['secret_name'],
        "registry-credential.lerentis.uploadfilter24.eu",
        namespace,
        name,
        config['custom_annotations'],
        config['labels']
    )
    secret = create_dockerlogin(
        logger,
        secret,
        secret_json_object["data"],
        username_ref,
        password_ref,
        registry)
    
    apply_owner_reference(secret, config['secret_namespace'], namespace)
    update_secret(logger, secret, config['secret_namespace'])


@kopf.on.delete('registry-credential.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    config = extract_secret_config(spec)
    delete_secret(logger, config['secret_name'], config['secret_namespace'])
