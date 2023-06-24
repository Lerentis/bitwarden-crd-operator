import os
import json
import subprocess


class BitwardenCommandException(Exception):
    pass


def get_secret_from_bitwarden(logger, id):
    return command_wrapper(logger, command=f"get item {id}")


def unlock_bw(logger):
    status_output = command_wrapper(logger, "status", False)
    status = status_output['data']['template']['status']
    if status == 'unlocked':
        logger.info("Already unlocked")
        return
    token_output = command_wrapper(logger, "unlock --passwordenv BW_PASSWORD")
    os.environ["BW_SESSION"] = token_output["data"]["raw"]
    logger.info("Signin successful. Session exported")


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
