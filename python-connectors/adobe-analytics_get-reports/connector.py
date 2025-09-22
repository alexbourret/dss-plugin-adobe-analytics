from dataiku.connector import Connector
from adobe_analytics_common import (
    get_connection_from_config, reorder_rows, dss_date_to_adobe
)
from adobe_client import AdobeClient
from safe_logger import SafeLogger
from records_limit import RecordsLimit
from dss_selector_choices import get_value_from_ui
from diagnostics import test_urls

logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])


class AdobeAnalyticsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info(
            "Starting plugin adobe-analytics v0.0.19 with config={}".format(
                logger.filter_secrets(config)
            )
        )
        organization_id, company_id, api_key, bearer_token, mock = get_connection_from_config(config)
        if mock:
            logger.warning("Mock mode ! Get mock server started")
        logger.info("Running diagnostics")
        logger.info("Pinging relevant external addresses:")
        test_urls()
        self.report_id = get_value_from_ui(config, "report_id")
        logger.info("selected rsid: {}".format(self.report_id))

        if not self.report_id:
            raise Exception("A valid Report Suite ID needs to be set")

        is_date_entered_manually = config.get("is_date_entered_manually", False)
        if not is_date_entered_manually:
            self.start_date = dss_date_to_adobe(config.get("start_date"))
            self.end_date = dss_date_to_adobe(config.get("end_date"))
        else:
            self.start_date = config.get("manual_start_date")
            self.end_date = config.get("manual_end_date")

        logger.info("selected date range: from {} to {}".format(self.start_date, self.end_date))

        column_index = 0
        metrics_ids = config.get("metrics_ids", [])
        self.metrics = []
        self.metrics_names = []
        for metric_name in metrics_ids:
            final_metric = {
                "columnId": "{}".format(column_index),
                "id": metric_name
            }
            self.metrics.append(final_metric)
            self.metrics_names.append(metric_name)
            column_index += 1

        self.dimension = get_value_from_ui(self.config, "dimension")
        self.segment = get_value_from_ui(self.config, "segment")

        self.client = AdobeClient(
            company_id=company_id,
            api_key=api_key,
            access_token=bearer_token,
            organization_id=organization_id,
            mock=mock
        )

    def get_read_schema(self):
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        logger.info("generate_rows, records_limit={}".format(records_limit))
        limit = RecordsLimit(records_limit)

        for row in reorder_rows(self.client.next_report_row(
                report_id=self.report_id, start_date=self.start_date, end_date=self.end_date,
                metrics=self.metrics, dimension=self.dimension, segment=self.segment
            ), self.metrics_names
        ):
            yield row
            if limit.is_reached():
                return

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None, write_mode="OVERWRITE"):
        raise NotImplementedError

    def get_partitioning(self):
        raise NotImplementedError

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        raise NotImplementedError
