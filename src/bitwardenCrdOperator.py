#!/usr/bin/env python3
import os
import kopf
import schedule
import time
import threading

from utils.utils import command_wrapper, unlock_bw, sync_bw

def bitwarden_signin(logger, **kwargs):
    if 'BW_HOST' in os.environ:
        try:
            home_dir = os.path.expanduser("~")
            bw_host_file = os.path.join(home_dir, ".bw_host")
            bw_host_env = os.getenv('BW_HOST')
            if os.path.isfile(bw_host_file):
                with open(bw_host_file, "r") as f:
                    saved_host = f.read().strip()
                if saved_host == bw_host_env:
                    if "DEBUG" in dict(os.environ):
                        logger.info("BW_HOST unchanged, skipping config server command")
                else:
                    command_wrapper(logger, "logout")
                    command_wrapper(logger, f"config server {bw_host_env}")
                    with open(bw_host_file, "w") as f:
                        f.write(bw_host_env)
            else:
                command_wrapper(logger, f"config server {bw_host_env}")
                with open(bw_host_file, "w") as f:
                    f.write(bw_host_env)
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
    logger.info("Loading schedules")
    bitwarden_signin(logger)

    bw_sync_interval = float(os.environ.get('BW_SYNC_INTERVAL', 900))
    bw_relogin_interval = float(os.environ.get('BW_RELOGIN_INTERVAL', 3600))

    schedule.every(bw_relogin_interval).seconds.do(bitwarden_signin, logger=logger)
    schedule.every(bw_sync_interval).seconds.do(sync_bw, logger=logger)
    run_continuously()
