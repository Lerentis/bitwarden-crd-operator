from utils.utils import get_secret_from_bitwarden, get_collection_secret_from_bitwarden, \
                        get_attachment, parse_fields_scope, parse_login_scope


class BitwardenLookupHandler:

    def __init__(self, logger) -> None:
        self.logger = logger

    def bitwarden_lookup(self, id, scope, field):
        if scope == "attachment":
            return get_attachment(self.logger, id, field)
        _secret_json = get_secret_with_id_from_bitwarden(self.logger, id)
        if scope == "login":
            return parse_login_scope(_secret_json, field)
        if scope == "fields":
            return parse_fields_scope(_secret_json, field)

    def bitwarden_lookup_with_name(self, collection_path, item_name, scope, field):
        _secret_json = get_collection_secret_from_bitwarden(self.logger, collection_path, item_name)
        if scope == "attachment":
            id = _secret_json['id']
            return get_attachment(self.logger, id, field)
        if scope == "login":
            return parse_login_scope(_secret_json, field)
        if scope == "fields":
            return parse_fields_scope(_secret_json, field)
