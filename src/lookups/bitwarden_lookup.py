import json

from utils.utils import get_secret_from_bitwarden, parse_fields_scope, parse_login_scope


def bitwarden_lookup(id, scope, field):
    _secret_json = get_secret_with_id_from_bitwarden(None, id)
    if scope == "login":
        return parse_login_scope(_secret_json, field)
    if scope == "fields":
        return parse_fields_scope(_secret_json, field)

def bitwarden_lookup_with_name(collection_path, item_name, scope, field):
    _secret_json = get_collection_secret_from_bitwarden(None, collection_path, item_name)
    if scope == "login":
        return parse_login_scope(_secret_json, field)
    if scope == "fields":
        return parse_fields_scope(_secret_json, field)
