#!/usr/bin/env python3
import kopf
import kubernetes
import base64
import os
import json

def get_secret_from_bitwarden(id):
    return command_wrapper(f" item {id}")

def command_wrapper(command):
    output = os.os.popen(f"bw {command}")
    return output

@kopf.on.startup()
def bitwarden_signin(logger, **kwargs):
    if 'BW_HOST' in os.environ:
        output = os.popen(f"bw config server {os.getenv('BW_HOST')}")
    else:
        logger.info(f"BW_HOST not set. Assuming SaaS installation")
    command_wrapper("login --apikey")
    token_output = command_wrapper("unlock --passwordenv BW_PASSWORD")
    for line in token_output:
        if "export BW_SESSION" in line:
            os.popen(line.replace("$", ""))

@kopf.on.create('bitwarden-secrets.lerentis.uploadfilter24.eu')
def create_fn(spec, name, namespace, logger, **kwargs):

    type = spec.get('type')
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    secret_json_object = json.loads(get_secret_from_bitwarden(id))

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-secrets.lerentis.uploadfilter24.eu",
        "managedObject": name
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name, annotations=annotations)
    secret.type = "Opaque"
    secret.data = {
            'username': str(base64.b64encode(secret_json_object["login.username"].encode("utf-8")), "utf-8"),
            'password': str(base64.b64encode(secret_json_object["login.password"].encode("utf-8")), "utf-8")
        }

    obj = api.create_namespaced_secret(
        secret_namespace, secret
    )

    logger.info(f"Secret {secret_namespace}/{secret_name} is created")


@kopf.on.update('bitwarden-secrets.lerentis.uploadfilter24.eu')
def my_handler(spec, old, new, diff, **_):
    pass

@kopf.on.delete('bitwarden-secrets.lerentis.uploadfilter24.eu')
def my_handler(spec, name, namespace, logger, **kwargs):
    pass