from adobe_auth import AdobeAuth
from adobe_pagination import AdobePagination
from api_client import APIClient
from safe_logger import SafeLogger


logger = SafeLogger("adobe-analytics plugin", ["bearer-token"])

class AdobeClient():
    def __init__(self, company_id=None, api_key=None, access_token=None):
        server_url = "https://analytics.adobe.io/api/{}".format(company_id)
        pagination = AdobePagination()
        self.client = APIClient(
            server_url=server_url,
            auth=AdobeAuth(api_key=api_key, bearer_token=access_token),
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

    def get(self, endpoint, url=None, raw=False):
        response = self.client.get(endpoint, url=url, raw=raw)
        return response

    def post(self, endpoint, url=None, raw=False, params=None, data=None, json=None, headers=None):
        response = self.client.post(endpoint, url=url, raw=raw, params=params, data=data, json=json, headers=headers)
        return response

    def patch(self, endpoint, url=None, raw=False, params=None, data=None, json=None, headers=None):
        response = self.client.patch(endpoint, url=url, raw=raw, params=params, data=data, json=json, headers=headers)
        return response

    def get_reports(self, report_id=None, start_date=None, end_date=None, metrics=None, dimensions=None):
        logger.info("get_report:report_id={}, start_date={}, end_date={}, metrics={}, dimensions={}".format(report_id, start_date, end_date, metrics, dimensions))
        query = {
            "rsid": report_id,
            "globalFilters":[
                {
                    "type": "dateRange",
                    "dateRange": "{}/{}".format(start_date, end_date)
                }
            ],
            "metricContainer": {
                "metrics": metrics
            },
            "dimension": dimensions[0],
            "settings": {
                "dimensionSort": "asc"
            }
        }
        logger.info("query={}".format(query))
        response = self.post("reports", json=query)
        if "error_code" in response:
            error_code = response.get("error_code")
            message = response.get("message")
            raise Exception("There was an error {}, {}. Please send the logs to the developpers.".format(error_code, message))
        return response
