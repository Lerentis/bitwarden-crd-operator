import os
import json
import subprocess
import distutils

bw_sync_interval = float(os.environ.get(
    'BW_SYNC_INTERVAL', 900))

class BitwardenCommandException(Exception):
    pass


def get_secret_from_bitwarden(logger, spec, force_sync=False):
    sync_bw(logger, force=force_sync)
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


def sync_bw(logger, force=False):

    def _sync(logger):
        status_output = command_wrapper(logger, command=f"sync")
        logger.info(f"Sync successful {status_output}")
        return

    if force:
        _sync(logger)
        return

    global_force_sync = bool(distutils.util.strtobool(
        os.environ.get('BW_FORCE_SYNC', "false")))

    if global_force_sync:
        logger.debug("Running forced sync")
        _sync(logger)
    else:
        logger.debug("Running scheduled sync")
        _sync(logger)


def get_attachment(logger, id, name):
    return command_wrapper(logger, command=f"get attachment {name} --itemid {id}", raw=True)


def unlock_bw(logger):
    status_output = command_wrapper(logger, "status", False)
    status = status_output['data']['template']['status']
    if status == 'unlocked':
        logger.info("Already unlocked")
        return
    token_output = command_wrapper(logger, "unlock --passwordenv BW_PASSWORD")
    os.environ["BW_SESSION"] = token_output["data"]["raw"]
    logger.info("Signin successful. Session exported")


def command_wrapper(logger, command, use_success: bool = True, raw: bool = False):
    system_env = dict(os.environ)
    response_flag = "--raw" if raw else "--response"
    final_command = f"bw {response_flag} {command}"
    sp = subprocess.Popen(
        [final_command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        shell=True,
        env=system_env)
    out, err = sp.communicate()
    if err:
        logger.warn(err)
        return None
    if "DEBUG" in system_env:
        logger.info(f"Command requested: {final_command}")
        logger.info(out.decode(encoding='UTF-8'))
    if raw:
        return out.decode(encoding='UTF-8')
    resp = json.loads(out.decode(encoding='UTF-8'))
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


def get_secret_with_id_from_bitwarden(logger, id):
    return command_wrapper(logger, command=f"get item {id}")["data"]


def get_collection_secret_from_bitwarden(logger, collection_path, item_name):
    collection_id = get_collection_from_bitwarden_with_path(logger, collection_path)
    bw_answer = command_wrapper(logger, command=f"list items --collectionid {collection_id} --search '{item_name}'")
    items = [obj for obj in bw_answer['data']['data'] if obj['name'] == item_name]
    if not items:
        raise BitwardenCommandException(f"No item with name '{item_name}' found in in '{collection_path}' collection")
    if len(items) > 1:
        raise BitwardenCommandException(f"Multiple items found with name '{item_name}' in '{collection_path}' collection - name must be unique.")
    return items[0]


def get_collection_from_bitwarden_with_path(logger, collection_path):
    bw_answer = command_wrapper(logger, command=f"list collections --search '{collection_path}'")
    collections = [obj for obj in bw_answer['data']['data'] if obj['name'] == collection_path]
    if not collections:
        raise BitwardenCommandException(f"No collection with path '{collection_path}' found.")
    if len(collections) > 1:
        raise BitwardenCommandException(f"Multiple collections found with path '{collection_path}' - path must be unique.")
    return collections[0]['id']
