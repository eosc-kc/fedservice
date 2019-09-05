import logging

from cryptojwt.jws.jws import factory
from oidcmsg.oidc import RegistrationRequest
from oidcmsg.oidc import RegistrationResponse
from oidcservice.exception import ResponseError
from oidcservice.oidc.registration import Registration

logger = logging.getLogger(__name__)


class FedRegistration(Registration):
    msg_type = RegistrationRequest
    response_cls = RegistrationResponse
    endpoint_name = 'federation_registration_endpoint'
    endpoint = 'registration'
    request_body_type = 'jose'
    response_body_type = 'jose'

    def __init__(self, service_context, state_db, conf=None,
                 client_authn_factory=None, **kwargs):
        Registration.__init__(self, service_context, state_db, conf=conf,
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
            iss=_fe.entity_id, sub=_fe.entity_id, metadata=_md, key_jar=_fe.key_jar,
            authority_hints=_fe.proposed_authority_hints)

    def parse_response(self, info, sformat="", state="", **kwargs):
        resp = self.parse_federation_response(info, state=state)

        if not resp:
            logger.error('Missing or faulty response')
            raise ResponseError("Missing or faulty response")

        return resp

    def parse_federation_response(self, resp, **kwargs):
        """
        Receives a dynamic client registration response,

        :param resp: An entity statement instance
        :return: A set of metadata claims
        """
        _sc = self.service_context
        _fe = _sc.federation_entity

        # Can not collect trust chain. Have to verify the signed JWT with keys I have

        kj = self.service_context.federation_entity.key_jar
        _jwt = factory(resp)
        entity_statement = _jwt.verify_compact(resp, keys=kj.get_jwt_verify_keys(_jwt.jwt))

        chosen = None
        for sup, fos in entity_statement['authority_hints'].items():
            for op_statement in _fe.op_statements:
                if op_statement.fo in fos:
                    chosen = op_statement
                    break

        # based on the Federation ID, conclude which OP config to use
        op_claims = chosen.metadata
        # _sc.trust_path = (chosen.fo, _fe.op_paths[statement.fo][0])
        _sc.provider_info = self.response_cls(**op_claims)

        return entity_statement['metadata'][_fe.entity_type]

    def update_service_context(self, resp, state='', **kwargs):
        Registration.update_service_context(self, resp, state, **kwargs)
        _fe = self.service_context.federation_entity
        _fe.iss = resp['client_id']