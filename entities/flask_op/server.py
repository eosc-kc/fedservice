#!/usr/bin/env python3
import argparse
import json
import logging
import os

# import OpenSSL
# import werkzeug
from oidcop.configure import Configuration
from oidcop.utils import create_context
from oidcop.utils import lower_or_upper

try:
    from .application import oidc_provider_init_app
except (ModuleNotFoundError, ImportError):
    from application import oidc_provider_init_app

dir_path = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)


def main(config_file, args):
    logging.basicConfig(level=logging.DEBUG)
    config = Configuration.create_from_config_file(config_file)
    app = oidc_provider_init_app(config)

    web_conf = config.webserver

    context = create_context(dir_path, web_conf)

    kwargs = {}

    if args.display:
        print(json.dumps(app.endpoint_context.provider_info, indent=4, sort_keys=True))
        exit(0)

    if args.insecure:
        app.endpoint_context.federation_entity.collector.insecure = True

    _cert = os.path.join(dir_path, lower_or_upper(web_conf, "server_cert"))
    app.endpoint_context.federation_entity.collector.web_cert_path = _cert

    app.run(host=web_conf['domain'], port=web_conf['port'],
            debug=web_conf['debug'], ssl_context=context,
            **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', dest='display', action='store_true')
    parser.add_argument('-t', dest='tls', action='store_true')
    parser.add_argument('-k', dest='insecure', action='store_true')
    parser.add_argument(dest="config")
    args = parser.parse_args()
    main(args.config, args)
