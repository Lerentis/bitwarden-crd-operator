import os
import json
import subprocess
import distutils

bw_sync_interval = float(os.environ.get(
    'BW_SYNC_INTERVAL', 900))

class BitwardenCommandException(Exception):
    pass


def get_secret_from_bitwarden(logger, id, force_sync=False):
    sync_bw(logger, force=force_sync)
    return command_wrapper(logger, command=f"get item {id}")


def sync_bw(logger, force=False):

    def _sync(logger):
        status = command_wrapper(logger, command=f"sync")
        if status is None:
            logger.info(f"Sync failed, retrying in {bw_sync_interval} seconds")
        return

    if force:
        _sync(logger)
        if "DEBUG" in dict(os.environ):
            logger.info("running with regular force sync enabled")
        return

    global_force_sync = bool(distutils.util.strtobool(
        os.environ.get('BW_FORCE_SYNC', "false")))

    if global_force_sync:
        _sync(logger)
        if "DEBUG" in dict(os.environ):
            logger.info("Running with global force sync")

    else:
        _sync(logger)


def get_attachment(logger, id, name):
    return command_wrapper(logger, command=f"get attachment {name} --itemid {id}", raw=True)


def unlock_bw(logger):
    status_output = command_wrapper(logger, "status", False)
    status = status_output['data']['template']['status']
    if status == 'unlocked':
        if "DEBUG" in dict(os.environ):
            logger.info("Already unlocked")
        return
    token_output = command_wrapper(logger, "unlock --passwordenv BW_PASSWORD")
    os.environ["BW_SESSION"] = token_output["data"]["raw"]
    logger.info("Signin successful. Session exported")


def command_wrapper(logger, command, use_success: bool = True, raw: bool = False):
    system_env = dict(os.environ)
    response_flag = "--raw" if raw else "--response"
    sp = subprocess.Popen(
        [f"bw {response_flag} {command}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        shell=True,
        env=system_env)
    out, err = sp.communicate()
    if err:
        logger.warn(err)
        return None
    if raw:
        return out.decode(encoding='UTF-8')
    if "DEBUG" in system_env:
        logger.info(out.decode(encoding='UTF-8'))
    resp = json.loads(out.decode(encoding='UTF-8'))
    if resp["success"] != None and (not use_success or (use_success and resp["success"] == True)):
        return resp
    logger.warn(resp)
    return None


def parse_login_scope(secret_json, key):
    return secret_json["data"]["login"][key]


def parse_fields_scope(secret_json, key):
    if "fields" not in secret_json["data"]:
        return None
    for entry in secret_json["data"]["fields"]:
        if entry['name'] == key:
            return entry['value']
