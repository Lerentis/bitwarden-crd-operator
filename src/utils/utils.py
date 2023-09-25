import os
import json
import subprocess
import distutils
from datetime import datetime, timezone, timedelta
from dateutil import parser
from dateutil.tz import tzutc
tzinfos = {"CDT": tzutc()}

bw_sync_interval = float(os.environ.get(
    'BW_SYNC_INTERVAL', 900))

class BitwardenCommandException(Exception):
    pass


def get_secret_from_bitwarden(logger, id, force_sync=False):
    sync_bw(logger, force=force_sync)
    return command_wrapper(logger, command=f"get item {id}")


def sync_bw(logger, force=False):

    def _sync(logger):
        status_output = command_wrapper(logger, command=f"sync")
        logger.info(f"Sync successful {status_output}")
        return

    if force:
        _sync(logger)
        return

    last_sync = last_sync_bw(logger)
    now = datetime.now(tzutc())
    sync_interval = timedelta(seconds=bw_sync_interval)
    bw_is_out_of_sync_inverval = (now - last_sync) >= sync_interval
    global_force_sync = bool(distutils.util.strtobool(
        os.environ.get('BW_FORCE_SYNC', "false")))
    needs_sync = force or global_force_sync or bw_is_out_of_sync_inverval
    logger.debug(f"last_sync: {last_sync}")
    logger.debug(
        f"force: {force}, global_force_sync: {global_force_sync}, bw_is_out_of_sync_inverval: {bw_is_out_of_sync_inverval}, needs_sync: {needs_sync}")

    if needs_sync:
        status_output = _sync(logger)
        logger.info(f"Sync successful {status_output}")


def last_sync_bw(logger):
    null_datetime_string = "0001-01-01T00:00:00.000Z"

    # retruns: {"success":true,"data":{"object":"string","data":"2023-09-22T13:50:09.995Z"}}
    last_sync_output = command_wrapper(
        logger, command="sync --last", use_success=False)

    # if not last_sync_output:
    #     return parser.parse(null_datetime_string, tzinfos=tzinfos)

    if not last_sync_output or not last_sync_output.get("success"):
        logger.error("Error getting last sync time.")
        return parser.parse(null_datetime_string, tzinfos=tzinfos)

    # in case no sync was done yet, null is returned from api
    # use some long ago date...
    last_sync_string = last_sync_output.get(
        "data").get("data", null_datetime_string)
    last_sync = parser.parse(last_sync_string, tzinfos=tzinfos)
    return last_sync


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
