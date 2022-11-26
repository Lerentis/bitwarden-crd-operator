import os
import subprocess

def get_secret_from_bitwarden(id):
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