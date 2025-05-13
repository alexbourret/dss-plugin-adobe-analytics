from adobe_auth import AdobeAuth
from adobe_pagination import AdobePagination
from api_client import APIClient
from safe_logger import SafeLogger


logger = SafeLogger("adobe-analytics plugin", ["bearer-token", "access_token", "client_secret"])


class AdobeClient():
    def __init__(self, company_id=None, api_key=None, access_token=None, organization_id=None):
        server_url = "https://analytics.adobe.io/api/{}".format(company_id)
        pagination = AdobePagination()
        self.client = APIClient(
            server_url=server_url,
            auth=AdobeAuth(api_key=api_key, bearer_token=access_token, organization_id=organization_id),
            pagination=pagination,
            max_number_of_retries=1
        )

    def get_next_item(self, endpoint):
        for page in self.get_next_page(endpoint):
            for item in page.get("results", []):
                yield item

    def get_next_page(self, endpoint):
        response = self.get(endpoint)
        return response

    def get(self, endpoint, url=None, params=None, raw=False):
        response = self.client.get(endpoint, url=url, params=params, raw=raw)
        return response

    def post(self, endpoint, url=None, raw=False, params=None, data=None, json=None, headers=None):
        response = self.client.post(endpoint, url=url, raw=raw, params=params, data=data, json=json, headers=headers)
        return response

    def patch(self, endpoint, url=None, raw=False, params=None, data=None, json=None, headers=None):
        response = self.client.patch(endpoint, url=url, raw=raw, params=params, data=data, json=json, headers=headers)
        return response

    def get_reports(self, report_id=None, start_date=None, end_date=None, metrics=None, dimension=None):
        logger.info("get_report:report_id={}, start_date={}, end_date={}, metrics={}, dimension={}".format(
                report_id, start_date, end_date, metrics, dimension
            )
        )
        query = {
            "rsid": report_id,
            "globalFilters": [
                {
                    "type": "dateRange",
                    "dateRange": "{}/{}".format(start_date, end_date)
                }
            ],
            "metricContainer": {
                "metrics": metrics
            },
            "dimension": dimension,
            "settings": {
            }
        }
        logger.info("query={}".format(query))
        response = self.post("reports", json=query)
        if "error_code" in response:
            error_code = response.get("error_code")
            message = response.get("message")
            raise Exception("There was an error {}, {}. Please send the logs to the developpers.".format(error_code, message))
        return response

    def list_report_suites(self):
        # GET https://analytics.adobe.io/api/{GLOBAL_COMPANY_ID}/reportsuites/collections/suites
        # response = self.get("reportsuites/collections/suites")
        report_suites = []
        row_index = 0
        for row in self.client.get_next_row("reportsuites/collections/suites", data_path="content"):
            report_suites.append(row)
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                break
            if row_index > 1000:
                logger.error("loop in list_report_suites")
                # just exploring, we don't want to block the plugin for that
                break
        logger.info("list_report_suites looped {} times".format(row_index))
        return report_suites

    def list_report_suites_all_pages(self):
        # No doc on pagination, so trying things...
        # GET https://analytics.adobe.io/api/{GLOBAL_COMPANY_ID}/reportsuites/collections/suites
        response = self.get("reportsuites/collections/suites", params={"page": 1})
        logger.info("page1:{}".format(response))
        response = self.get("reportsuites/collections/suites", params={"page": 2})
        logger.info("page2:{}".format(response))
        response = self.get("reportsuites/collections/suites", params={"page": 3})
        logger.info("page3:{}".format(response))
        response = self.get("reportsuites/collections/suites", params={"page": 4})
        logger.info("page4:{}".format(response))
        response = self.get("reportsuites/collections/suites", params={"page": 5})
        logger.info("page5:{}".format(response))
        return response


def generate_access_token(user_account):
    import requests
    logger.info("Generating access token")
    url = "https://ims-na1.adobelogin.com/ims/token/v3"
    client_id = user_account.get("client_id")
    client_secret = user_account.get("client_secret")
    scope = user_account.get("scope")
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": scope
    }
    logger.info("data={}".format(logger.filter_secrets(data)))
    response = requests.post(url=url, data=data)
    status_code = response.status_code
    logger.info("generate_access_token status:{}".format(status_code))
    token = response.json()
    logger.info("generate_access_token response:{}".format(logger.filter_secrets(token)))
    if "error" in token:
        raise Exception("Error {} ({}): {}".format(status_code, token.get("error"), token.get("error_description", "")))
    return token.get("access_token")
