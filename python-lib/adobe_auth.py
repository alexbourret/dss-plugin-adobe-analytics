import requests


class AdobeAuth(requests.auth.AuthBase):
    def __init__(self, api_key=None, bearer_token=None):
        self.api_key = api_key
        self.bearer_token = bearer_token

    def __call__(self, request):
        if self.api_key is not None:
            request.headers["x-api-key"] = "{}".format(
                self.api_key
            )
        if self.bearer_token is not None:
            request.headers["Authorization"] = "Bearer {}".format(
                self.bearer_token
            )
        return request
