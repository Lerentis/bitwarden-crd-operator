#!/usr/bin/env python3
import kopf

@kopf.on.create('bitwarden-secrets.lerentis.uploadfilter24')
def create_fn(body, **kwargs):

    # The all-purpose function for the event creation.
    kopf.event(body, type="SomeType", reason="SomeReason", message="Some message")

    # The shortcuts for the conventional events and common cases.
    kopf.info(body, reason="SomeReason", message="Some message")
    kopf.warn(body, reason="SomeReason", message="Some message")

    try:
        raise RuntimeError("Exception text.")
    except Exception:
        kopf.exception(body, reason="SomeReason", message="Some exception:")
