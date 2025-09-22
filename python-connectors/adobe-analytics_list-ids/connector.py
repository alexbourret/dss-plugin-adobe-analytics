from dataiku.connector import Connector
from records_limit import RecordsLimit
from adobe_client import AdobeClient
from safe_logger import SafeLogger
from adobe_analytics_common import (
    get_connection_from_config
)
from plugin_details import get_initialization_string


logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])


class ListIDsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info("{} ListIDsConnector with config={}".format(
            get_initialization_string(),
            logger.filter_secrets(config)
        ))

        self.element_to_list = self.config.get("element_to_list", "reports")
        self.report_id_manual = self.config.get("report_id_manual", None)
        if self.report_id_manual == '':
            self.report_id_manual = None

        organization_id, company_id, api_key, bearer_token, mock = get_connection_from_config(config)
        self.client = AdobeClient(
            company_id=company_id,
            api_key=api_key,
            access_token=bearer_token,
            organization_id=organization_id,
            mock=mock
        )

    def get_read_schema(self):
        # In this example, we don't specify a schema here, so DSS will infer the schema
        # from the columns actually returned by the generate_rows method
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        next = self.client.next_report_suites()
        if self.element_to_list == "metrics":
            next = self.client.next_metric(self.report_id_manual)
        elif self.element_to_list == "calculated_metrics":
            next = self.client.next_calculated_metric(self.report_id_manual)
        elif self.element_to_list == "dimensions":
            next = self.client.next_dimension(self.report_id_manual)
        elif self.element_to_list == "segments":
            next = self.client.next_segment(self.report_id_manual)
        for item in next:
            yield item
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
