from dataiku.connector import Connector
from adobe_analytics_common import (
    get_connection_from_config, reorder_rows, get_date_range
)
from adobe_cja_client import AdobeCJAClient
from safe_logger import SafeLogger
from records_limit import RecordsLimit
from dss_selector_choices import get_value_from_ui
from diagnostics import test_urls
from project_variable import ProjectVariable
from adobe_accumulator import Accumulator
import json

logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])
mock = ProjectVariable("dku_adobe-analytics_is-mock", default_value=False).get_value()


class AdobeCJAConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info(
            "Starting plugin adobe-analytics v0.0.26 with config={}".format(
                logger.filter_secrets(config)
            )
        )
        if mock:
            logger.warning("Mock mode ! Get mock server started")
        self.should_dump_server_result = config.get("should_dump_server_result", False)
        logger.info("Running diagnostics")
        # logger.info("External IP={}".format(get_kernel_external_ip()))
        # logger.info("Internal IP={}".format(get_kernel_internal_ip()))
        logger.info("Pinging relevant external addresses:")
        test_urls()
        self.report_id = get_value_from_ui(config, "report_id")
        logger.info("selected rsid: {}".format(self.report_id))
        if not self.report_id:
            raise Exception("A valid Report Suite ID needs to be set")
        self.start_date, self.end_date = get_date_range(config)
        logger.info("selected date range: from {} to {}".format(self.start_date, self.end_date))
        column_index = 0
        metrics_ids = config.get("metrics_ids", [])
        self.metrics = []
        self.metrics_names = []
        for metric_dict in metrics_ids:
            metric_name, metric_id = decode_metric_id(metric_dict)
            final_metric = {
                "columnId": "{}".format(column_index),
                "id": metric_id
            }
            self.metrics.append(final_metric)
            self.metrics_names.append(metric_name)
            column_index += 1
        logger.info("metrics={}".format(self.metrics))
        logger.info("metrics_names={}".format(self.metrics_names))

        # self.dimension = get_value_from_ui(self.config, "dimension")
        self.dimension_names, self.dimensions = decode_metric_id(
            get_value_from_ui(self.config, "dimensions")
        )

        self.segment = get_value_from_ui(self.config, "segment")
        auth_type = config.get("auth_type", "user_account")
        logger.info("auth_type={}".format(auth_type))
        user_account = config.get(auth_type, {})
        bearer_token = user_account.get("bearer_token")
        organization_id = user_account.get("organization_id")
        company_id = user_account.get("company_id")
        api_key = user_account.get("api_key")
        self.should_add_total_row = config.get("should_add_total_row", False)
        self.should_provide_breakdown_data = config.get("should_provide_breakdown_data", False)

        organization_id, company_id, api_key, bearer_token = get_connection_from_config(config, mock=mock)
        self.client = AdobeCJAClient(
            company_id=company_id,
            api_key=api_key,
            access_token=bearer_token,
            organization_id=organization_id,
            mock=mock
        )

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
        accumulator = Accumulator()

        if self.should_dump_server_result:
            # Dumping result for analysis in case of multiple dimensions
            # remove this when issue fixed
            response = self.client.next_report_row(
                report_id=self.report_id, start_date=self.start_date, end_date=self.end_date,
                metrics=self.metrics, dimensions=self.dimensions, segment=self.segment, dump_response=True
            )
            response = next(next(response))
            yield response
        else:
            for row in reorder_rows(self.client.next_report_row(
                    report_id=self.report_id, start_date=self.start_date, end_date=self.end_date,
                    metrics=self.metrics, dimensions=self.dimensions, segment=self.segment
                ), self.metrics_names  #, item_names=self.dimension_names
            ):
                row["start_date"] = self.start_date
                row["end_date"] = self.end_date
                if self.should_add_total_row:
                    accumulator.add_row(row)
                # row.pop("item_name", None)
                yield order_output_row(row, self.metrics_names)  #, item_name=self.dimension_name)
                if limit.is_reached():
                    return
            if self.should_add_total_row:
                total_row = accumulator.get_total()
                total_row["item_id"] = None
                total_row["item_name"] = "Total"
                yield order_output_row(total_row, self.metrics_names)  #, item_name=self.dimension_name)

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


def decode_metric_id(metric_dict):
    json_metric = metric_dict
    try:
        json_metric = json.loads(metric_dict)
    except Exception:
        pass

    if isinstance(json_metric, dict):
        return json_metric.get("name"), json_metric.get("id")
    else:
        return json_metric, json_metric


def metrics_with_names(metrics, metrics_names):
    named_metrics = []
    for metric, metric_name in zip(metrics, metrics_names):
        named_metric = metric
        named_metric["name"] = metric_name
        named_metrics.append(named_metric)
    return named_metrics


def order_output_row(row, metrics_names, item_name=None):
    # metrics_names=['Page Views', 'Unique Visitors']
    item_name = item_name or "item_name"
    ordered_row = {}
    preferred_columns = [
        "item_id",
        "dimension_1",
        item_name
    ]
    preferred_columns.extend(metrics_names or [])
    preferred_columns.extend([
        "report_id",
        "start_date",
        "end_date",
        "metrics",
        "segment"
    ])
    for column in preferred_columns:
        if column in row and column not in ordered_row:
            ordered_row[column] = row.get(column)

    remaining_columns = sorted([column for column in row.keys() if column not in ordered_row])
    for column in remaining_columns:
        ordered_row[column] = row.get(column)
    return ordered_row
