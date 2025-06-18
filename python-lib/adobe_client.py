from adobe_auth import AdobeAuth
from adobe_pagination import AdobePagination
from api_client import APIClient
from safe_logger import SafeLogger


logger = SafeLogger("adobe-analytics plugin", ["bearer-token", "access_token", "client_secret"])


class AdobeClient():
    def __init__(self, company_id=None, api_key=None, access_token=None, organization_id=None, mock=False):
        if mock:
            logger.warning("Mock mode !")
            server_url = "http://localhost:3001/api/{}".format(company_id)
        else:
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

    def get_reports(self, report_id=None, start_date=None, end_date=None,
                    metrics=None, dimension=None, segment=None):
        # doc: https://developer.adobe.com/analytics-apis/docs/2.0/guides/endpoints/reports/
        # segments are added in the globalFilters : 
        #       https://developer.adobe.com/analytics-apis/docs/2.0/guides/endpoints/reports/segments/

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
        if segment:
            query["globalFilters"].append({
                "type": "segment",
                "segmentId": segment
            })
        logger.info("query={}".format(query))
        response = self.post("reports", json=query)
        if "error_code" in response:
            error_code = response.get("error_code")
            message = response.get("message")
            raise Exception("There was an error {}, {}. Please send the logs to the developpers.".format(error_code, message))
        return response

    def next_report_row(self, report_id=None, start_date=None, end_date=None,
                        metrics=None, dimension=None, segment=None):
        # doc: https://developer.adobe.com/analytics-apis/docs/2.0/guides/endpoints/reports/
        # segments are added in the globalFilters :
        #       https://developer.adobe.com/analytics-apis/docs/2.0/guides/endpoints/reports/segments/

        logger.info("next_report_row:report_id={}, start_date={}, end_date={}, metrics={}, dimension={}".format(
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
        if segment:
            query["globalFilters"].append({
                "type": "segment",
                "segmentId": segment
            })
        logger.info("query={}".format(query))
        for row in self.client.get_next_row("reports", data_path="rows"):
            yield row

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

    def next_report_suites(self):
        # GET https://analytics.adobe.io/api/{GLOBAL_COMPANY_ID}/reportsuites/collections/suites
        # response = self.get("reportsuites/collections/suites")
        # if mock is True:
        #     for row in [{'collectionItemType': 'reportsuite', 'id': 'reporta', 'name': 'Report A', 'rsid': 'reporta'}, {'collectionItemType': 'reportsuite', 'id': 'reportb', 'name': 'Report B', 'rsid': 'reportb'}]:
        #         yield row
        #     return
        row_index = 0
        for row in self.client.get_next_row("reportsuites/collections/suites", data_path="content"):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            if row_index > 1000:
                logger.error("infinite loop in next_report_suites")
                # just exploring, we don't want to block the plugin for that
                return
            yield row

    def next_metric(self, rsid):
        # if mock is True:
        #     for row in [{"id": "metrics/campaigninstances", "name": "Campaign Click-throughs"}, {"id": "metrics/cartadditions", "name": "Cart Additions"}]:
        #         yield row
        #     return
        row_index = 0
        for row in self.client.get_next_row("metrics", params={
                    "rsid": rsid
        }):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            if row_index > 1000:
                logger.error("infinite loop in next_metric")
                # just exploring, we don't want to block the plugin for that
                return
            yield row

    def next_dimension(self, rsid):
        # if mock is True:
        #     for row in [{"id": "variables/campaign", "name": "Tracking Code"}, {"id": "variables/clickmaplink", "name": "Activity Map Link"}]:
        #         yield row
        #     return
        row_index = 0
        for row in self.client.get_next_row("dimensions", params={
                    "rsid": rsid
        }):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            if row_index > 1000:
                logger.error("infinite loop in next_dimension")
                # just exploring, we don't want to block the plugin for that
                return
            yield row

    def next_segment(self, rsid):
        row_index = 0
        for row in self.client.get_next_row("segments", data_path="content", params={
                    "rsid": rsid
        }):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            if row_index > 1000:
                logger.error("infinite loop in next_segment")
                # just exploring, we don't want to block the plugin for that
                return
            yield row

    def list_report_metrics(self, rsid):
        # https://developer.adobe.com/analytics-apis/docs/2.0/guides/endpoints/metrics/
        metrics = []
        for row in self.client.get_next_row(
                "metrics",
                params={
                    "rsid": rsid
                }
        ):
            metrics.append(row)
        return metrics

    def list_report_dimensions(self, rsid):
        # https://developer.adobe.com/analytics-apis/docs/2.0/guides/endpoints/dimensions/
        dimensions = []
        for row in self.client.get_next_row(
                "dimensions",
                params={
                    "rsid": rsid
                }
        ):
            dimensions.append(row)
        return dimensions

    def list_report_segments(self, rsid):
        # https://developer.adobe.com/analytics-apis/docs/2.0/guides/endpoints/segments/
        segments = []
        for row in self.client.get_next_row(
                "segments",
                params={
                    "rsid": rsid
                },
                data_path="content"
        ):
            segments.append(row)
        return segments


def generate_access_token(user_account, mock=False):
    import requests
    logger.info("Generating access token")
    if mock:
        logger.info("Mock mode !")
        url = "http://localhost:3001/ims/token/v3"
    else:
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
