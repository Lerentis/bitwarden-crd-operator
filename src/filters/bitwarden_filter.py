from utils.utils import get_secret_from_bitwarden


def datetime_format(value, format="%H:%M %d-%m-%y"):
    return value.strftime(format)

def bitwarden_lookup(value, id, field):
    pass