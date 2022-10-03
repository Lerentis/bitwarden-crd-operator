#!/usr/bin/env python3
import kopf
import kubernetes
import base64
import os
import subprocess
import json

from pprint import pprint

def get_secret_from_bitwarden(logger, id):
    return command_wrapper(logger, f"get item {id}")

def unlock_bw(logger):
    token_output = command_wrapper(logger, "unlock --passwordenv BW_PASSWORD")
    tokens = token_output.split('"')[1::2]
    os.environ["BW_SESSION"] = tokens[1]
    logger.info("Signin successful. Session exported")

def command_wrapper(logger, command):
    system_env = dict(os.environ)
    sp = subprocess.Popen([f"bw {command}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=True, env=system_env)
    out, err = sp.communicate()
    if err:
        logger.warn(f"Error during bw cli invokement: {err}")
    return out.decode(encoding='UTF-8')

@kopf.on.startup()
def bitwarden_signin(logger, **kwargs):
    if 'BW_HOST' in os.environ:
        command_wrapper(logger, f"config server {os.getenv('BW_HOST')}")
    else:
        logger.info(f"BW_HOST not set. Assuming SaaS installation")
    command_wrapper(logger, "login --apikey")
    unlock_bw(logger)

@kopf.on.create('bitwarden-secrets.lerentis.uploadfilter24.eu')
def create_managed_secret(spec, name, namespace, logger, body, **kwargs):

    content_def = body['spec']['content']
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    unlock_bw(logger)
    
    secret_json_object = json.loads(get_secret_from_bitwarden(logger, id))

    api = kubernetes.client.CoreV1Api()

    annotations = {
        "managed": "bitwarden-secrets.lerentis.uploadfilter24.eu",
        "managedObject": f"{namespace}/{name}"
    }
    secret = kubernetes.client.V1Secret()
    secret.metadata = kubernetes.client.V1ObjectMeta(name=secret_name, annotations=annotations)
    secret.type = "Opaque"
    secret.data = {}
    for eleml in content_def:
        for k, elem in eleml.items():
            for key,value in elem.items():
                if key == "secretName":
                    _secret_key = value
                if key == "secretRef":
                    _secret_ref = value
            
            secret.data[_secret_ref] = str(base64.b64encode(secret_json_object["login"][_secret_key].encode("utf-8")), "utf-8")

    obj = api.create_namespaced_secret(
        secret_namespace, secret
    )

    logger.info(f"Secret {secret_namespace}/{secret_name} is created")


@kopf.on.update('bitwarden-secrets.lerentis.uploadfilter24.eu')
def my_handler(spec, old, new, diff, **_):
    pass

@kopf.on.delete('bitwarden-secrets.lerentis.uploadfilter24.eu')
def delete_managed_secret(spec, name, namespace, logger, **kwargs):
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')
    api = kubernetes.client.CoreV1Api()

    try:
        api.delete_namespaced_secret(secret_name, secret_namespace)
        logger.info(f"Secret {secret_namespace}/{secret_name} has been deleted")
    except:
        logger.warn(f"Could not delete secret {secret_namespace}/{secret_name}!")
