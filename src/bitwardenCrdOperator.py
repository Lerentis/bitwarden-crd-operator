#!/usr/bin/env python3
import os
import kopf
import schedule
import time
import threading
import logging

from utils.utils import command_wrapper, unlock_bw, sync_bw, ERROR_COUNT

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

def run_continuously(interval=30):
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run

@kopf.on.startup()
def load_schedules(logger, **kwargs):
    logging.getLogger('aiohttp.access').setLevel(logging.ERROR)
    bitwarden_signin(logger)
    logger.info("Loading schedules")
    bw_relogin_interval = float(os.environ.get('BW_RELOGIN_INTERVAL', 3600))
    bw_sync_interval = float(os.environ.get('BW_SYNC_INTERVAL', 900))
    schedule.every(bw_relogin_interval).seconds.do(bitwarden_signin, logger=logger)
    logger.info(f"relogin scheduled every {bw_relogin_interval} seconds")
    schedule.every(bw_sync_interval).seconds.do(sync_bw, logger=logger)
    logger.info(f"sync scheduled every {bw_relogin_interval} seconds")
    stop_run_continuously = run_continuously()

@kopf.on.probe()
def healthcheck(**kwargs):
    if ERROR_COUNT != 0:
        return ERROR_COUNT