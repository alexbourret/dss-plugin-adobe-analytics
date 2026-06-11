from adobe_client import AdobeClient, ErrorHandler
from safe_logger import SafeLogger


logger = SafeLogger("adobe-analytics cja plugin", ["bearer-token", "access_token", "client_secret"])


class AdobeCJAClient(AdobeClient):
    def _get_server_url(self, company_id, is_mock):
        if is_mock:
            logger.warning("Mock mode ! Get mock server started")
            server_url = "http://localhost:3001/"
        else:
            server_url = "https://cja.adobe.io/"
        return server_url

    def next_report_row(self, report_id=None, start_date=None, end_date=None,
                        metrics=None, dimensions=None, segment=None, dump_response=False):
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
        elif isinstance(dimensions, list) and len(dimensions) == 1:
            query["dimension"] = dimensions[0]
        elif isinstance(dimensions, list) and len(dimensions) == 0:
            query["dimension"] = None
        else:
            query["dimension"] = dimensions
        if segment:
            query["globalFilters"].append({
                "type": "segment",
                "segmentId": segment
            })
        logger.info("query={}".format(query))
        error_handling = ErrorHandler()
        if dump_response:
            response = self.client.get_response("reports", method="POST", json=query)
            yield response
        else:
            for row in self.client.get_next_row("reports", data_path="rows", method="POST", json=query, error_handling=error_handling):
                yield row

    def next_data_views(self):
        # from https://developer.adobe.com/cja-apis/docs/endpoints/dataviews/
        # GET https://cja.adobe.io/data/dataviews
        row_index = 0
        for row in self.client.get_next_row("data/dataviews", data_path="content"):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            yield row

    def next_metric(self, rsid):
        # from https://developer.adobe.com/cja-apis/docs/endpoints/metrics/
        # GET https://cja.adobe.io/data/dataviews/{DATAVIEW_ID}/metrics
        row_index = 0
        for row in self.client.get_next_row(
            "data/dataviews/{}/metrics".format(rsid),
            data_path="content"
        ):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            yield row

    def next_dimension(self, rsid):
        # from https://developer.adobe.com/cja-apis/docs/endpoints/dimensions/
        # GET https://cja.adobe.io/data/dataviews/{dataviewId}/dimensions
        row_index = 0
        for row in self.client.get_next_row(
            "data/dataviews/{}/dimensions".format(rsid),
            data_path="content"
        ):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            yield row

    def next_segment(self, rsid):
        # from https://developer.adobe.com/cja-apis/docs/endpoints/segments/
        # GET https://cja.adobe.io/segments
        row_index = 0
        for row in self.client.get_next_row("segments", params={"includeType": "all"}):
            row_index += 1
            if row is None:
                logger.error("empty row, stopping here")
                return
            yield row
