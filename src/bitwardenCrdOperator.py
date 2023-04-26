#!/usr/bin/env python3
import os
import kopf

from utils.utils import command_wrapper, unlock_bw


@kopf.on.startup()
def bitwarden_signin(logger, **kwargs):
    if 'BW_HOST' in os.environ:
        try:
            command_wrapper(logger, f"config server {os.getenv('BW_HOST')}")
        except BaseException:
            logger.warn("Received non-zero exit code from server config")
            logger.warn("This is expected from startup")
            pass
    else:
        logger.info("BW_HOST not set. Assuming SaaS installation")
    command_wrapper(logger, "login --apikey")
    unlock_bw(logger)
