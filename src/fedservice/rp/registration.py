import logging

from cryptojwt.jws.jws import factory
from oidcmsg.oidc import RegistrationRequest
from oidcmsg.oidc import RegistrationResponse
from oidcservice.exception import ResponseError
from oidcservice.oidc import registration

from fedservice.entity_statement.collect import branch2lists
from fedservice.entity_statement.collect import unverified_entity_statement
from fedservice.entity_statement.policy import apply_policy
from fedservice.entity_statement.policy import combine_policy
from fedservice.entity_statement.verify import eval_policy_chain

logger = logging.getLogger(__name__)


class Registration(registration.Registration):
    msg_type = RegistrationRequest
    response_cls = RegistrationResponse
    endpoint_name = 'federation_registration_endpoint'
    request_body_type = 'jose'
    response_body_type = 'jose'

    def __init__(self, service_context, conf=None, client_authn_factory=None, **kwargs):
        registration.Registration.__init__(self, service_context, conf=conf,
                                           client_authn_factory=client_authn_factory)
        #
        self.post_construct.append(self.create_entity_statement)

    @staticmethod
    def carry_receiver(request, **kwargs):
        if 'receiver' in kwargs:
            return request, {'receiver': kwargs['receiver']}
        else:
            return request, {}

    def create_entity_statement(self, request_args, service=None, **kwargs):
        """
        Create a self signed entity statement

        :param request_args:
        :param service:
        :param kwargs:
        :return:
        """

        _fe = self.service_context.federation_entity
        _md = {_fe.entity_type: request_args.to_dict()}
        return _fe.create_entity_statement(
            iss=_fe.entity_id, sub=_fe.entity_id, metadata=_md, key_jar=_fe.keyjar,
            authority_hints=_fe.proposed_authority_hints)

    def parse_response(self, info, sformat="", state="", **kwargs):
        resp = self.parse_federation_registration_response(info, **kwargs)

        if not resp:
            logger.error('Missing or faulty response')
            raise ResponseError("Missing or faulty response")

        return resp

    def _get_trust_anchor_id(self, entity_statement):
        _metadata = entity_statement.get('metadata')
        if not _metadata:
            return None

        _fed_entity = _metadata.get('federation_entity')
        if not _fed_entity:
            return None

        _trust_anchor_id = _fed_entity.get('trust_anchor_id')
        return _trust_anchor_id

    def get_trust_anchor_id(self, entity_statement):
        if len(self.service_context.federation_entity.op_statements) == 1:
            _id = self.service_context.federation_entity.op_statements[0].fo
            _tai = self._get_trust_anchor_id(entity_statement)
            if _tai and _tai != _id:
                logger.warning(
                    "The trust anchor id given in the registration response does not match what "
                    "is in the discovery document")
                ValueError('Trust Anchor Id mismatch')
        else:
            _id = self._get_trust_anchor_id(entity_statement)
            if _id is None:
                raise ValueError("Don't know which trust anchor to use")
        return _id

    def parse_federation_registration_response(self, resp, **kwargs):
        """
        Receives a dynamic client registration response,

        :param resp: An entity statement instance
        :return: A set of metadata claims
        """
        _sc = self.service_context
        _fe = _sc.federation_entity

        # Can not collect trust chain. Have to verify the signed JWT with keys I have

        kj = self.service_context.federation_entity.keyjar
        _jwt = factory(resp)
        entity_statement = _jwt.verify_compact(resp, keys=kj.get_jwt_verify_keys(_jwt.jwt))

        _trust_anchor_id = self.get_trust_anchor_id(entity_statement)

        chosen = None
        for op_statement in _fe.op_statements:
            if op_statement.fo == _trust_anchor_id:
                chosen = op_statement
                break

        if not chosen:
            raise ValueError('No matching federation operator')

        # based on the Federation ID, conclude which OP config to use
        op_claims = chosen.metadata
        # _sc.trust_path = (chosen.fo, _fe.op_paths[statement.fo][0])
        _sc.provider_info = self.response_cls(**op_claims)

        # To create RPs metadata collect the trust chains
        tree = {}
        for ah in _fe.authority_hints:
            tree[ah] = _fe.collector.collect_intermediate(_fe.entity_id, ah)

        _node = {_fe.entity_id: (resp, tree)}
        chains = branch2lists(_node)

        # Get the policies
        policy_chains_tup = [eval_policy_chain(c, _fe.keyjar, _fe.entity_type) for c in chains]
        _policy = combine_policy(policy_chains_tup[0][1],
                                 entity_statement['metadata_policy'][_fe.entity_type])
        logger.debug("Combined policy: {}".format(_policy))
        _uev = unverified_entity_statement(kwargs["request_body"])
        logger.debug("Registration request: {}".format(_uev))
        _query = _uev["metadata"][_fe.entity_type]
        _sc.registration_response = apply_policy(_query, _policy)
        return _sc.registration_response

    def update_service_context(self, resp, **kwargs):
        registration.Registration.update_service_context(self, resp, **kwargs)
        _fe = self.service_context.federation_entity
        _fe.iss = resp['client_id']

    def get_response_ext(self, url, method="GET", body=None, response_body_type="",
                         headers=None, **kwargs):
        """

        :param url:
        :param method:
        :param body:
        :param response_body_type:
        :param headers:
        :param kwargs:
        :return:
        """

        _collector = self.service_context.federation_entity.collector

        httpc_args = _collector.httpc_parms.copy()
        # have I seen it before
        cert_path = _collector.get_cert_path(self.service_context.provider_info["issuer"])
        if cert_path:
            httpc_args["verify"] = cert_path

        try:
            resp = _collector.http_cli(method, url, data=body, headers=headers, **httpc_args)
        except Exception as err:
            logger.error('Exception on request: {}'.format(err))
            raise

        if 300 <= resp.status_code < 400:
            return {'http_response': resp}

        if "keyjar" not in kwargs:
            kwargs["keyjar"] = self.service_context.keyjar
        if not response_body_type:
            response_body_type = self.response_body_type

        if response_body_type == 'html':
            return resp.text

        if body:
            kwargs['request_body'] = body

        return self.parse_response(resp, response_body_type, **kwargs)
