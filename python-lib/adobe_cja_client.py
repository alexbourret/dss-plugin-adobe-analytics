from adobe_client import AdobeClient, ErrorHandler
from safe_logger import SafeLogger


logger = SafeLogger("adobe-analytics cja plugin", ["bearer-token", "access_token", "client_secret"])


class AdobeCJAClient(AdobeClient):
    def _get_server_url(self, company_id, is_mock):
        if is_mock:
            logger.warning("Mock mode ! Get mock server started")
            server_url = "http://localhost:3001/api/{}".format(company_id)
        else:
            server_url = "https://cja.adobe.io/{}".format(company_id)
        return server_url

    def next_report_row(self, report_id=None, start_date=None, end_date=None,
                        metrics=None, dimensions=None, segment=None):
        logger.info("next_report_row:report_id={}, start_date={}, end_date={}, metrics={}, dimension={}".format(
                report_id, start_date, end_date, metrics, dimensions
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
            "settings": {
            }
        }
        if isinstance(dimensions, list) and len(dimensions) > 1:
            query["dimensions"] = dimensions
        elif isinstance(dimensions, list):
            query["dimension"] = dimensions[0]
        else:
            query["dimension"] = dimensions
        if segment:
            query["globalFilters"].append({
                "type": "segment",
                "segmentId": segment
            })
        logger.info("query={}".format(query))
        error_handling = ErrorHandler()
        for row in self.client.get_next_row("reports", data_path="rows", method="POST", json=query, error_handling=error_handling):
            yield row
