from dataiku.connector import Connector
from mock import Mock
from adobe_analytics_common import (
    get_connection_from_config, reorder_rows
)
from adobe_client import AdobeClient
from safe_logger import SafeLogger
from records_limit import RecordsLimit
from dss_selector_choices import get_value_from_ui

logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])
mock = False


class AdobeAnalyticsConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info(
            "Starting plugin adobe-analytics v0.0.12 with config={}".format(
                logger.filter_secrets(config)
            )
        )
        if mock:
            logger.warning("Mock mode ! Get mock server started")
        # logger.info("Running diagnostics")
        # logger.info("External IP={}".format(get_kernel_external_ip()))
        # logger.info("Internal IP={}".format(get_kernel_internal_ip()))
        # logger.info("Pinging relevant external addresses:")
        # test_urls()
        # {
        #     'metrics': [],
        #     'dimensions': ['variables/daterangeday'],
        #     'user_account': {
        #         'company_id': 'dataiku',
        #         'api_key': '1234'
        #     },
        #     'auth_type': 'user_account',
        #     'report_id': 'azer'
        # }
        self.report_id = get_value_from_ui(config, "report_id")
        logger.info("selected rsid: {}".format(self.report_id))
        if not self.report_id:
            raise Exception("A valid Report Suite ID needs to be set")
        self.start_date = dss_date_to_adobe(config.get("start_date"))
        self.end_date = dss_date_to_adobe(config.get("end_date"))
        # metrics = config.get("metrics", [])
        # logger.info("ALX:metrics={}".format(metrics))
        # [{
        #     '$$hashKey': 'object:583',
        #     'metric_name': 'metrics/visits'
        # }, {
        #     '$$hashKey': 'object:605',
        #     'metric_name': 'metrics/pageviews',
        #     'metric_sort': 'asc'
        # }, {
        #     '$$hashKey': 'object:627',
        #     'metric_name': 'metrics/visitors',
        #     'metric_sort': 'desc'
        # }]
        column_index = 0
        metrics_ids = config.get("metrics_ids", [])
        self.metrics = []
        self.metrics_names = []
        for metric_name in metrics_ids:
            # metric_id = get_value_from_ui(metric, "value")
            # metric_sort = metric.get("metric_sort")
            final_metric = {
                "columnId": "{}".format(column_index),
                "id": metric_name
            }
            # if metric_sort:
            #     final_metric["sort"] = metric_sort
            self.metrics.append(final_metric)
            self.metrics_names.append(metric_name)
            column_index += 1
        logger.info("metrics={}".format(self.metrics))
        logger.info("metrics_names={}".format(self.metrics_names))

        # self.dimension = self.config.get("dimension")
        self.dimension = get_value_from_ui(self.config, "dimension")
        self.segment = get_value_from_ui(self.config, "segment")
        auth_type = config.get("auth_type", "user_account")
        logger.info("auth_type={}".format(auth_type))
        user_account = config.get(auth_type, {})
        bearer_token = user_account.get("bearer_token")
        organization_id = user_account.get("organization_id")
        company_id = user_account.get("company_id")
        api_key = user_account.get("api_key")
        self.pagination_type = config.get("pagination_type", "params")
        logger.info("Pagination type set to {}.".format(self.pagination_type))
        # if auth_type == "server_to_server":
        #     logger.info("auth type is server_to_server")
        #     bearer_token = generate_access_token(user_account, mock=mock)
        #     api_key = user_account.get("client_id")
        """
        def get_connection_from_config(config):
            auth_type = config.get("auth_type", "user_account")
            logger.info("auth_type={}".format(auth_type))
            user_account = config.get(auth_type, {})
            bearer_token = user_account.get("bearer_token")
            organization_id = user_account.get("organization_id")
            company_id = user_account.get("company_id")
            api_key = user_account.get("api_key")
            if auth_type == "server_to_server":
                logger.info("auth type is server_to_server")
                bearer_token = generate_access_token(user_account)
                api_key = user_account.get("client_id")
            return organization_id, company_id, api_key, bearer_token
        """
        organization_id, company_id, api_key, bearer_token = get_connection_from_config(config, mock=mock)
        self.client = AdobeClient(
            company_id=company_id,
            api_key=api_key,
            access_token=bearer_token,
            organization_id=organization_id,
            mock=mock,
            pagination_type=self.pagination_type
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
        # json_response = self.client.get_reports(
        #     report_id=self.report_id,
        #     start_date=self.start_date,
        #     end_date=self.end_date,
        #     metrics=self.metrics,
        #     dimension=self.dimension,
        #     segment=self.segment
        # )
        # logger.info("json_response={}".format(json_response))
        # rows = reorder_response(json_response, self.metrics_names)
        # # rows = reorder_response(Mock.JSON_RESPONSE, ['metrics/pageviews','metrics/visits','metrics/visitors'])
        # for row in rows:
        #     yield row
        #     if limit.is_reached():
        #         return
        for row in reorder_rows(self.client.next_report_row(
                report_id=self.report_id, start_date=self.start_date, end_date=self.end_date,
                metrics=self.metrics, dimension=self.dimension, segment=self.segment
            ), self.metrics_names
        ):
            yield row
            if limit.is_reached():
                return
        # performance_timer.start()
        # rows = json_response.get("rows", [])
        # data_frame  = pandas.DataFrame(json_response['rows'])
        # data_frame.columns = [self.dimensions[0]+'_key',self.dimensions[0],'data']
        # dfa = pandas.DataFrame(data_frame['data'].to_list())
        # dfa.columns = ['metrics/pageviews','metrics/visits','metrics/visitors']
        # output = pandas.concat([data_frame.iloc[:,:-1],dfa],axis='columns')
        # performance_timer.stop()
        # # {'total_duration': 0.005134105682373047, 'number_of_events': 1, 'average_time': 0.005134105682373047}
        # print("ALX:time = {}".format(performance_timer.get_report()))
        # #print("ALX:output={}".format(output))
        # #for row in rows:
        # #    yield row
        # #output['json'] = output.apply(lambda x: x.to_json(), axis=1)
        # print("ALX:output2={}".format(output))
        # for index, output_row in output.iterrows():
        #     print("output_row={}/{}".format(output_row.to_json(), dir(output_row)))
        #     print("ALX:before:{}".format(output_row.to_json()))
        #     yield output_row.to_dict()
        #     print("ALX:after")
        # #for i in xrange(1,10):
        # #    yield { "first_col" : str(i), "my_string" : "Yes" }
        # https://analytics.adobe.io/api/[client id]/[endpoint]?rsid=[report suite id]
        # https://analytics.adobe.io/api/{}/reports

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


class CustomDatasetWriter(object):
    def __init__(self):
        pass

    def write_row(self, row):
        """
        Row is a tuple with N + 1 elements matching the schema passed to get_writer.
        The last element is a dict of columns not found in the schema
        """
        raise NotImplementedError

    def close(self):
        pass


def dss_date_to_adobe(dss_date):
    if not dss_date or not isinstance(dss_date, str):
        return None
    if dss_date.endswith("Z"):
        return dss_date[:-1]
