import json

from utils.utils import get_secret_from_bitwarden, get_attachment, parse_fields_scope, parse_login_scope


def bitwarden_lookup(id, scope, field):
    if scope == "attachment":
        return get_attachment(None, id, field)
    _secret_json = get_secret_from_bitwarden(None, id)
    if scope == "login":
        return parse_login_scope(_secret_json, field)
    if scope == "fields":
        return parse_fields_scope(_secret_json, field)
