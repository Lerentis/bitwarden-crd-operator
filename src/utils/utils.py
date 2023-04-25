import os
import json
import subprocess


class BitwardenCommandException(Exception):
    pass

def get_secret_from_bitwarden(logger, spec):
    if 'id' in spec:
        id = spec.get('id')
        logger.info(f"Looking up secret with ID: {id}")
        return get_secret_with_id_from_bitwarden(logger, id)
    elif 'itemName' in spec and 'collectionPath' in spec:
        item_name = spec.get('itemName')
        collection_path = spec.get('collectionPath')
        logger.info(f"Looking up '{item_name}' secret in '{collection_path}' collection")
        return get_collection_secret_from_bitwarden(logger, collection_path, item_name)
    else:
        raise BitwardenCommandException("Either 'id' or ('itemName' and 'collectionPath') need to be provided")

def get_secret_with_id_from_bitwarden(logger, id):
    return command_wrapper(logger, command=f"get item {id}")["data"]

def get_collection_secret_from_bitwarden(logger, collection_path, item_name):
    collection_id = get_collection_from_bitwarden_with_path(logger, collection_path)
    items = command_wrapper(logger, command=f"list items --collectionid {collection_id}")["data"]["data"]
    items = [obj for obj in items if obj['name'] == item_name]
    if not items:
        raise BitwardenCommandException(f"No item with name '{item_name}' found in in '{collection_path}' collection")
    if len(items) > 1:
        raise BitwardenCommandException(f"Multiple items found with name '{item_name}' in '{collection_path}' collection - name must be unique.")
    return items[0]

def get_collection_from_bitwarden_with_path(logger, collection_path):
    collections = command_wrapper(logger, command=f"list collections")['data']['data']
    collections = [obj for obj in collections if obj['name'] == collection_path]
    if not collections:
        raise BitwardenCommandException(f"No collection with path '{collection_path}' found.")
    if len(collections) > 1:
        raise BitwardenCommandException(f"Multiple collections found with path '{collection_path}' - path must be unique.")
    return collections[0]['id']

def unlock_bw(logger):
    status_output = command_wrapper(logger, "status", False)
    status = status_output['data']['template']['status']
    if status == 'unlocked':
        logger.info("Already unlocked")
        return
    token_output = command_wrapper(logger, "unlock --passwordenv BW_PASSWORD")
    os.environ["BW_SESSION"] = token_output["data"]["raw"]
    logger.info("Signin successful. Session exported")
    # Vault needs to be sync regularly
    command_wrapper(logger, "sync")

def command_wrapper(logger, command, use_success: bool = True):
    system_env = dict(os.environ)
    sp = subprocess.Popen(
        [f"bw --response {command}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        shell=True,
        env=system_env)
    out, err = sp.communicate()
    resp = json.loads(out.decode(encoding='UTF-8'))
    if "DEBUG" in system_env:
        logger.info(resp)
    if resp["success"] != None and (not use_success or (use_success and resp["success"] == True)):
        return resp
    logger.warn(resp)
    return None


def parse_login_scope(secret_json, key):
    return secret_json["login"][key]


def parse_fields_scope(secret_json, key):
    if "fields" not in secret_json:
        return None
    for entry in secret_json["fields"]:
        if entry['name'] == key:
            return entry['value']
