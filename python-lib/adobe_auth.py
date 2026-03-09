import requests
from safe_logger import SafeLogger
import datetime
import hashlib
import random
import base64


logger = SafeLogger("adobe-analytics plugin AdobeAuth", ["x-api-key", "Authorization"])


class AdobeAuth(requests.auth.AuthBase):
    def __init__(self, api_key=None, bearer_token=None, organization_id=None, username=None, password=None):
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.organization_id = organization_id
        self.username = username
        self.password = password

    def __call__(self, request):
        if self.api_key is not None:
            request.headers["x-api-key"] = "{}".format(
                self.api_key
            )
        if self.bearer_token is not None:
            request.headers["Authorization"] = "Bearer {}".format(
                self.bearer_token
            )
        if self.organization_id is not None:
            request.headers["x-gw-ims-org-id"] = self.organization_id
        if self.username is not None and self.password is not None:
            request.headers["x-wsse"] = get_wsse_header(
                self.username,
                self.password
            )
        logger.info("requests headers : {}".format(logger.filter_secrets(request.headers)))
        return request


def get_wsse_header(username, secret):
    # From https://catalinmunteanu.com/xwsse-token-python.html
    created = datetime.datetime.utcnow().isoformat()
    nonce = hashlib.md5(str(random.getrandbits(128)).encode('utf-8')).hexdigest()
    digest = "".join((nonce, created, secret))
    digest = hashlib.sha256(digest.encode('utf-8')).hexdigest()
    digest = base64.b64encode(digest.encode("utf-8")).decode('utf-8')
    return ('UsernameToken Username="{username}", '
            'PasswordDigest="{digest}", Nonce="{nonce}", '
            'Created="{created}"').format(
                username=username,
                digest=digest,
                nonce=nonce,
                created=created
            )
