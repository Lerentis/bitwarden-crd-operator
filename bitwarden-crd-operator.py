#!/usr/bin/env python3
import os
import kopf
import kubernetes
from jinja2 import Environment, FileSystemLoader


@kopf.on.create('bitwarden-secrets.lerentis.uploadfilter24.eu')
def create_fn(spec, name, namespace, logger, **kwargs):

    type = spec.get('type')
    id = spec.get('id')
    secret_name = spec.get('name')
    secret_namespace = spec.get('namespace')

    api = kubernetes.client.CoreV1Api()

    environment = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '/templates')))

    template = environment.get_template('username-password.yaml.j2')
    data = template.render(
        original_crd=name,
        secret_name=secret_name,
        namespace=secret_namespace,
        username="test",
        password="test"
    )

    obj = api.create_namespaced_secret(
        namespace=secret_namespace,
        body=data
    )

    logger.info(f"Secret {name} is created: {obj}")


@kopf.on.update('bitwarden-secrets.lerentis.uploadfilter24.eu')
def my_handler(spec, old, new, diff, **_):
    pass

@kopf.on.delete('bitwarden-secrets.lerentis.uploadfilter24.eu')
def my_handler(spec, **_):
    pass