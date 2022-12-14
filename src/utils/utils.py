import os
import subprocess

class BitwardenCommandException(Exception):
    pass

def get_secret_from_bitwarden(id):
    return command_wrapper(command=f"get item {id}")

def unlock_bw(logger):
    token_output = command_wrapper("unlock --passwordenv BW_PASSWORD")
    tokens = token_output.split('"')[1::2]
    os.environ["BW_SESSION"] = tokens[1]
    logger.info("Signin successful. Session exported")

def command_wrapper(command):
    system_env = dict(os.environ)
    sp = subprocess.Popen([f"bw {command}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=True, env=system_env)
    out, err = sp.communicate()
    if err:
        raise BitwardenCommandException(err)
    return out.decode(encoding='UTF-8')

def parse_login_scope(secret_json, key):
    return secret_json["login"][key]

def parse_fields_scope(secret_json, key):
    for entry in secret_json["fields"]:
        if entry['name'] == key:
            return entry['value']
