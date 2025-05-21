from dataiku.connector import Connector
from adobe_analytics_common import (
    reorder_response, get_connection_from_config, dss_date_to_adobe
)
from adobe_client import AdobeClient
from safe_logger import SafeLogger
from records_limit import RecordsLimit
from dss_selector_choices import get_value_from_ui

logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])
mock = True


class AdobeAnalyticsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info(
            "Starting plugin adobe-analytics v0.0.11 with config={}".format(
                logger.filter_secrets(config)
            )
        )
        if mock:
            logger.warning("Mock mode !")
        self.report_id = get_value_from_ui(config, "report_id")
        logger.info("selected rsid: {}".format(self.report_id))
        if not self.report_id:
            raise Exception("A valid Report Suite ID needs to be set")
        self.start_date = dss_date_to_adobe(config.get("start_date"))
        self.end_date = dss_date_to_adobe(config.get("end_date"))
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
        logger.info("metrics={}".format(self.metrics))
        logger.info("metrics_names={}".format(self.metrics_names))

        self.dimension = get_value_from_ui(self.config, "dimension")
        auth_type = config.get("auth_type", "user_account")
        logger.info("auth_type={}".format(auth_type))
        user_account = config.get(auth_type, {})
        bearer_token = user_account.get("bearer_token")
        organization_id = user_account.get("organization_id")
        company_id = user_account.get("company_id")
        api_key = user_account.get("api_key")

        organization_id, company_id, api_key, bearer_token = get_connection_from_config(config, mock=mock)
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
        logger.info("Before get_reports")
        json_response = self.client.get_reports(
            report_id=self.report_id,
            start_date=self.start_date,
            end_date=self.end_date,
            metrics=self.metrics,
            dimension=self.dimension
        )
        logger.info("json_response={}".format(json_response))
        rows = reorder_response(json_response, self.metrics_names)
        for row in rows:
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
