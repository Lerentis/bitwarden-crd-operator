from utils.utils import get_secret_from_bitwarden

def bitwarden_lookup(id, field):
    _secret_json = get_secret_from_bitwarden(id)
    return _secret_json["login"][field]