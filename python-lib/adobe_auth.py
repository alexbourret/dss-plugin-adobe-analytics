import requests
from safe_logger import SafeLogger


logger = SafeLogger("adobe-analytics plugin AdobeAuth", ["x-api-key", "Authorization"])


class AdobeAuth(requests.auth.AuthBase):
    def __init__(self, api_key=None, bearer_token=None, organization_id=None):
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.organization_id = organization_id

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
        logger.info("requests headers : {}".format(logger.filter_secrets(request.headers)))
        return request
