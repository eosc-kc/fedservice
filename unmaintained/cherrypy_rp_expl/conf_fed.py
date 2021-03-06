PORT = 8089
BASEURL = "https://localhost:{}".format(PORT)

# If BASE is https these has to be specified
SERVER_CERT = "certs/cert.pem"
SERVER_KEY = "certs/key.pem"
CA_BUNDLE = None

VERIFY_SSL = False

KEYDEFS = [{"type": "RSA", "key": '', "use": ["sig"]},
           {"type": "EC", "crv": "P-256", "use": ["sig"]}]

PRIVATE_JWKS_PATH = "jwks_dir/jwks.json"
PUBLIC_JWKS_PATH = 'static/jwks.json'
# information used when registering the client, this may be the same for all OPs

CLIENT_PREFS = {
    "application_type": "web", "application_name": "rphandler",
    "contacts": ["ops@example.com"],
    "response_types": ["code", "id_token", "id_token token",
                       "code id_token", "code id_token token",
                       "code token"],
    "scope": ["openid", "profile", "email", "address", "phone"],
    "token_endpoint_auth_method": ["client_secret_basic",
                                   'client_secret_post']
    }

# Default set if nothing else is specified
SERVICES = {
    'FedProviderInfoDiscovery': {}, 'FedRegistrationRequest': {},
    'Authorization': {}, 'AccessToken': {},
    'RefreshAccessToken': {}, 'UserInfo': {}
}

client_config = {
    'client_preferences': {
        "application_type": "web", "application_name": "rphandler",
        "contacts": ["ops@example.com"],
        "response_types": ["code", "id_token", "id_token token",
                           "code id_token", "code id_token token",
                           "code token"],
        "scope": ["openid", "profile", "email", "address", "phone"],
        "token_endpoint_auth_method": ["client_secret_basic",
                                       'client_secret_post']
        },
    'issuer': 'https://catalogix.se',
    'federation': {
        'entity_id': BASEURL,
        'signing_keys':{
            'private_path': './entity_keys.json',
            'key_defs': KEYDEFS,
            'public_path': './pub_entity_keys.json'
        },
        'authority_hints': 'authority_hints.json',
        'trusted_roots': 'trusted_roots.json',
        'priority': [],
        'entity_type': 'openid_relying_party',
        'opponent_entity_type': 'openid_provider'
        # 'default_lifetime': 86400
    },
    'services': {
        'FedProviderInfoDiscovery': {}, 'FedRegistrationRequest': {},
        'Authorization': {}, 'AccessToken': {}, 'WebFinger': {},
        'RefreshAccessToken': {}, 'UserInfo': {}
    }
}

# The keys in this dictionary are the OPs short user friendly name
# not the issuer (iss) name.
# The special key '' is ued for OPs that support dynamic interactions.

CLIENTS = {
    # The ones that support web finger, OP discovery and client registration
    # This is the default, any client that is not listed here is expected to
    # support dynamic discovery and registration.
    "": client_config,
    }

# Whether an attempt to fetch the userinfo should be made
USERINFO = True
