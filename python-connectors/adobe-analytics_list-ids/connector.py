from dataiku.connector import Connector
from records_limit import RecordsLimit
from adobe_client import AdobeClient
from safe_logger import SafeLogger
from adobe_analytics_common import (
    get_connection_from_config, get_fine_tuning
)
from dss_selector_choices import get_value_from_ui
from plugin_details import get_initialization_string
from project_variable import ProjectVariable


logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])


class ListIDsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info("{} ListIDsConnector with config={}".format(
            get_initialization_string(),
            logger.filter_secrets(config)
        ))
        mock = ProjectVariable("dku_adobe-analytics_is-mock", default_value=False).get_value()
        self.element_to_list = self.config.get("element_to_list", "reports")
        self.report_id = get_value_from_ui(config, "report_id")
        auth_type = config.get("auth_type", "user_account")
        logger.info("auth_type={}".format(auth_type))
        user_account = config.get(auth_type, {})
        bearer_token = user_account.get("bearer_token")
        organization_id = user_account.get("organization_id")
        company_id = user_account.get("company_id")
        api_key = user_account.get("api_key")

        organization_id, company_id, api_key, bearer_token = get_connection_from_config(config, mock=mock)
        calculated_metrics_include_type_all, dimensions_reportable, segments_include_type_all, calculated_metrics_tobeusedinrsid = get_fine_tuning(config)
        self.client = AdobeClient(
            company_id=company_id,
            api_key=api_key,
            access_token=bearer_token,
            organization_id=organization_id,
            calculated_metrics_include_type_all=calculated_metrics_include_type_all, dimensions_reportable=dimensions_reportable, segments_include_type_all=segments_include_type_all, calculated_metrics_tobeusedinrsid=calculated_metrics_tobeusedinrsid,
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
            next = self.client.next_metric(self.report_id)
        elif self.element_to_list == "calculated_metrics":
            next = self.client.next_calculated_metric(self.report_id)
        elif self.element_to_list == "dimensions":
            next = self.client.next_dimension(self.report_id)
        elif self.element_to_list == "segments":
            next = self.client.next_segment(self.report_id)
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
