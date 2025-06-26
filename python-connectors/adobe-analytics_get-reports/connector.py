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
mock = False


class AdobeAnalyticsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info(
            "Starting plugin adobe-analytics v0.0.15 with config={}".format(
                logger.filter_secrets(config)
            )
        )
        if mock:
            logger.warning("Mock mode ! Get mock server started")
        logger.info("Running diagnostics")
        # logger.info("External IP={}".format(get_kernel_external_ip()))
        # logger.info("Internal IP={}".format(get_kernel_internal_ip()))
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
        logger.info("metrics={}".format(self.metrics))
        logger.info("metrics_names={}".format(self.metrics_names))

        self.dimension = get_value_from_ui(self.config, "dimension")
        self.segment = get_value_from_ui(self.config, "segment")
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

        logger.info("Testing pagination on report_suites...")
        try:
            report_suites = self.client.list_report_suites()
            logger.info("report_suites={}".format(report_suites))
        except Exception as error:
            logger.error("Error {} while listing report suites".format(error))

        logger.info("Testing pagination on metrics for {}...".format(self.report_id))
        try:
            report_metrics = self.client.list_report_metrics(self.report_id)
            logger.info("report_metrics={}".format(report_metrics))
        except Exception as error:
            logger.error("Error {} while listing report metrics".format(error))

        logger.info("Testing pagination on dimensions for {}...".format(self.report_id))
        try:
            report_dimensions = self.client.list_report_dimensions(self.report_id)
            logger.info("report_metrics={}".format(report_dimensions))
        except Exception as error:
            logger.error("Error {} while listing report dimensions".format(error))

        logger.info("Testing pagination on segments for {}...".format(self.report_id))
        try:
            report_segments = self.client.list_report_segments(self.report_id)
            logger.info("report_segments={}".format(report_segments))
        except Exception as error:
            logger.error("Error {} while listing report segments".format(error))

        logger.info("Testing getting info on report suite {}".format(self.report_id))
        # Goal: find the report's timezone to translate the UI date range
        try:
            report_info = self.client.get_report_suite_details(self.report_id)
            logger.info("Details about {}: {}".format(self.report_id, report_info))
        except Exception as error:
            logger.error("Error {} while getting details".format(error))

    def get_read_schema(self):
        """
        Returns the schema that this connector generates when returning rows.

        The returned schema may be None if the schema is not known in advance.
        In that case, the dataset schema will be infered from the first rows.

        If you do provide a schema here, all columns defined in the schema
        will always be present in the output (with None value),
        even if you don't provide a value in generate_rows

        The schema must be a dict, with a single key: "columns", containing an array of
        {'name':name, 'type' : type}.

        Example:
            return {"columns" : [ {"name": "col1", "type" : "string"}, {"name" :"col2", "type" : "float"}]}

        Supported types are: string, int, bigint, float, double, date, boolean
        """

        # In this example, we don't specify a schema here, so DSS will infer the schema
        # from the columns actually returned by the generate_rows method
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        logger.info("generate_rows, records_limit={}".format(records_limit))
        limit = RecordsLimit(records_limit)
        logger.info("Before get_reports")

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
        """
        Returns a writer object to write in the dataset (or in a partition).

        The dataset_schema given here will match the the rows given to the writer below.

        write_mode can either be OVERWRITE or APPEND.
        It will not be APPEND unless the plugin explicitly supports append mode. See flag supportAppend in connector.json.
        If applicable, the write_mode should be handled in the plugin code.

        Note: the writer is responsible for clearing the partition, if relevant.
        """
        raise NotImplementedError

    def get_partitioning(self):
        """
        Return the partitioning schema that the connector defines.
        """
        raise NotImplementedError

    def list_partitions(self, partitioning):
        """Return the list of partitions for the partitioning scheme
        passed as parameter"""
        return []

    def partition_exists(self, partitioning, partition_id):
        """Return whether the partition passed as parameter exists

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        """
        Returns the count of records for the dataset (or a partition).

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError
