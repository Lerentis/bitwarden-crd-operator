import kopf 
from filters.bitwarden_filter import bitwarden_lookup
from jinja2 import Environment


Environment.filters["bitwarden"] = bitwarden_lookup

