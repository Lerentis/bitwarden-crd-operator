#!/usr/bin/env python3
import os
import kopf
import schedule
import time
import threading

from utils.utils import BitwardenCommandException, command_wrapper, unlock_bw, sync_bw


AUTH_FAILURE_THRESHOLD = 3
auth_failures = 0


def _configure_bw_host(logger):
    if "BW_HOST" in os.environ:
        try:
            home_dir = os.path.expanduser("~")
            bw_host_file = os.path.join(home_dir, ".bw_host")
            bw_host_env = os.getenv("BW_HOST")
            if bw_host_env is None:
                return
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
    else:
        logger.info("BW_HOST not set. Assuming SaaS installation")


def _auth_failure_threshold(logger):
    configured_threshold = os.environ.get(
        "BW_AUTH_FAILURE_THRESHOLD", str(AUTH_FAILURE_THRESHOLD)
    )
    try:
        threshold = int(configured_threshold)
        if threshold < 1:
            raise ValueError("BW_AUTH_FAILURE_THRESHOLD must be greater than 0")
        return threshold
    except ValueError:
        logger.warn(
            f"Invalid BW_AUTH_FAILURE_THRESHOLD '{configured_threshold}', using {AUTH_FAILURE_THRESHOLD}"
        )
        return AUTH_FAILURE_THRESHOLD


def recover_auth_state(logger):
    os.environ.pop("BW_SESSION", None)
    command_wrapper(logger, "logout", use_success=False)

    home_dir = os.path.expanduser("~")
    cli_data_file = os.path.join(home_dir, ".config", "Bitwarden CLI", "data.json")
    if os.path.isfile(cli_data_file):
        try:
            os.remove(cli_data_file)
            logger.warn("Removed Bitwarden CLI cache file to recover auth state")
        except OSError as exc:
            logger.warn(f"Could not remove Bitwarden CLI cache file: {exc}")


def _login_and_unlock(logger):
    login_result = command_wrapper(logger, "login --apikey")
    if login_result is None:
        raise BitwardenCommandException("bw login failed")
    unlock_bw(logger)


def bitwarden_signin(logger, **kwargs):
    global auth_failures

    _configure_bw_host(logger)
    failure_threshold = _auth_failure_threshold(logger)

    try:
        _login_and_unlock(logger)
        if auth_failures > 0:
            logger.info("Authentication recovered")
        auth_failures = 0
        return
    except BitwardenCommandException as exc:
        auth_failures += 1
        logger.error(
            f"Authentication failed ({auth_failures}/{failure_threshold}): {exc}"
        )

    if auth_failures < failure_threshold:
        return

    logger.warn(
        "Authentication failure threshold reached, recovering Bitwarden auth state"
    )
    recover_auth_state(logger)

    try:
        _login_and_unlock(logger)
        auth_failures = 0
        logger.info("Authentication recovery succeeded")
    except BitwardenCommandException as exc:
        logger.error(f"Authentication recovery failed: {exc}")


def run_continuously(interval=30):
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        def run(self):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run


def safe_bitwarden_signin(logger, **kwargs):
    """Wrapper for bitwarden_signin that prevents schedule job cancellation on errors."""
    try:
        bitwarden_signin(logger, **kwargs)
    except Exception as e:
        logger.error(f"Relogin failed: {e}. Will retry on next schedule.")


def safe_sync_bw(logger, **kwargs):
    """Wrapper for sync_bw that prevents schedule job cancellation on errors."""
    try:
        sync_bw(logger, **kwargs)
    except Exception as e:
        logger.error(f"Sync failed: {e}. Will retry on next schedule.")


@kopf.on.startup()
def load_schedules(logger, **kwargs):
    logger.info("Loading schedules")
    bitwarden_signin(logger)

    bw_sync_interval = float(os.environ.get("BW_SYNC_INTERVAL", 900))
    bw_relogin_interval = float(os.environ.get("BW_RELOGIN_INTERVAL", 3600))

    schedule.every(bw_relogin_interval).seconds.do(safe_bitwarden_signin, logger=logger)
    schedule.every(bw_sync_interval).seconds.do(safe_sync_bw, logger=logger)
    run_continuously()
