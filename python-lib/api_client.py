import requests
from safe_logger import SafeLogger


logger = SafeLogger("api-client")


class APIClient():
    def __init__(self, server_url, auth, pagination=None, max_number_of_retries=None, should_fail_silently=False):
        self.session = requests.Session()
        self.server_url = server_url
        self.session.auth = auth
        self.number_of_retries = None
        self.page_offset = None
        self.pagination = pagination or DefaultPagination()
        self.max_number_of_retries = max_number_of_retries or 1
        self.should_fail_silently = should_fail_silently

    def get(self, endpoint, url=None, params=None, data=None, json=None, raw=False):
        if url:
            full_url = url
        else:
            full_url = self.get_full_url(endpoint)
        response = None
        while self.should_try_again(response):
            try:
                logger.info("getting url={}, params={}".format(full_url, params))
                response = self.session.get(full_url, params=params, data=data, json=json)
            except Exception as error:
                error_message = "Error on get: {}".format(error)
                logger.error(error_message)
                self.raise_if_necessary(error_message)
        display_response_error(response)
        if raw:
            return response
        json_response = response.json()
        return json_response

    def post(self, endpoint, url=None, params=None, json=None, data=None, headers=None, raw=False):
        if url:
            full_url = url
        else:
            full_url = self.get_full_url(endpoint)
        logger.info("posting url={}, params={}, json={}, data={}".format(full_url, params, json, data))
        json, params = reorganize_request_for_post_pagination(json, params)
        response = self.session.post(
            full_url,
            params=params,
            json=json,
            data=data,
            headers=headers
        )
        display_response_error(response)
        if raw:
            return response
        json_response = {}
        try:
            json_response = response.json()
        except Exception as error:
            logger.error("Could not convert response to json. Error '{}'".format(error))
            logger.error("Dumping content: {}".format(response.content))
        return json_response

    def patch(self, endpoint, url=None, params=None, json=None, data=None, headers=None, raw=False):
        if url:
            full_url = url
        else:
            full_url = self.get_full_url(endpoint)
        response = self.session.patch(
            full_url,
            params=params,
            json=json,
            data=data,
            headers=headers
        )
        display_response_error(response)
        if raw:
            return response
        json_response = response.json()
        return json_response

    def get_full_url(self, endpoint):
        full_url = "{}/{}".format(self.server_url, endpoint)
        return full_url

    def get_next_row(self, endpoint, url=None, method=None, data_path=None, params=None, json=None, data=None):
        method = method or "GET"
        params = params or {}
        response = None
        items_retrieved = 0
        while self.pagination.has_next_page(response, items_retrieved):
            params = self.pagination.get_paging_parameters(params)
            if method == "GET":
                response = self.get(endpoint, url=url, params=params, json=json, data=data, raw=True)
            else:
                response = self.post(endpoint, url=url, params=params, json=json, data=data, raw=True)
            items_retrieved = 0
            json_response = response.json()
            for row in get_next_row_from_response(json_response, data_path):
                items_retrieved += 1
                yield row

    def should_try_again(self, response):
        if response is not None:
            self.number_of_retries = None
            return False
        if self.number_of_retries is None:
            logger.warning("Retrying")
            self.number_of_retries = 1
        else:
            logger.warning("Retry {}".format(self.number_of_retries))
            self.number_of_retries += 1
        if self.number_of_retries > self.max_number_of_retries:
            self.number_of_retries = None
            logger.error("Max number of retries")
            return False
        return True

    def raise_if_necessary(self, error_message):
        if self.should_fail_silently:
            return
        else:
            if self.max_number_of_retries == self.max_number_of_retries:
                raise Exception(error_message)
            else:
                return


def get_next_row_from_response(response, data_path=None):
    # if not data_path:
    #     return response
    data = []
    if isinstance(data_path, str):
        data = response.get(data_path)
    elif isinstance(data_path, list):
        data = response
        for data_path_token in data_path:
            data = data.get(data_path_token, {})
    elif isinstance(response, list):
        data = response
    else:
        logger.error("get_next_row_from_response response={}".format(response))
        raise Exception("get_next_row_from_response: data_path not matching response type")
    if isinstance(data, list):
        for row in data:
            yield row
    else:
        yield data


class DefaultPagination():
    def __init__(self):
        # No pagination, just stops after the first page
        logger.info("Single page pagination used")
        pass

    def has_next_page(self, response, items_retrieved):
        logger.info("DefaultPagination:has_next_page")
        if response is None:
            logger.info("DefaultPagination:has_next_page initialisation")
            return True
        logger.info("DefaultPagination:has_next_page Stop here")
        return False

    def get_paging_parameters(self):
        logger.info("DefaultPagination:get_paging_parameters")
        return {}


def display_response_error(response):
    if response is None:
        logger.error("Empty response")
    elif isinstance(response, requests.Response):
        status_code = response.status_code
        logger.info("status_code={}".format(status_code))
        if status_code >= 400:
            logger.error("Error {}. Dumping response:{}".format(status_code, response.content))
    else:
        logger.error("Not a requests.Response object")


def reorganize_request_for_post_pagination(json, params):
    # For post, move paging parameters from query string to json form
    json = {} or json
    params = {} or params
    logger.warning("Reorganizing pagination from params {} to json {}".format(params, json))
    page = params.pop("page", None)
    if page is not None:
        settings = json.pop("settings", {})
        settings["page"] = page
        json["settings"] = settings
    logger.warning("New params {} and json {}".format(params, json))
    return json, params
