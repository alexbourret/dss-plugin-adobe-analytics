from dataiku.connector import Connector
from mock import Mock
from adobe_analytics_common import reorder_response
from adobe_client import AdobeClient, generate_access_token
from safe_logger import SafeLogger
from records_limit import RecordsLimit


logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key"])


class AdobeAnalyticsConnector(Connector):

    def __init__(self, config, plugin_config):
        """
        The configuration parameters set up by the user in the settings tab of the
        dataset are passed as a json object 'config' to the constructor.
        The static configuration parameters set up by the developer in the optional
        file settings.json at the root of the plugin directory are passed as a json
        object 'plugin_config' to the constructor
        """
        Connector.__init__(self, config, plugin_config)  # pass the parameters to the base class
        logger.info(
            "Starting plugin adobe-analytics v0.0.3 with config={}".format(
                logger.filter_secrets(config)
            )
        )
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
        self.report_id = config.get("report_id")
        self.start_date = config.get("start_date")
        self.end_date = config.get("end_date")
        self.metrics = config.get("metrics", [])
        # self.metrics = []
        # print("ALX:metrics={}".format(metrics))
        # for metric in metrics:
        #     print("ALX:metric={}".format(metric))
        #     metric_value = metric.get("value")
        #     self.metrics.append({"id": metric_value})
        self.dimensions = self.config.get("dimensions", [])
        auth_type = config.get("auth_type", "user_account")
        logger.info("auth_type={}".format(auth_type))
        user_account = config.get(auth_type, {})
        bearer_token = user_account.get("bearer_token")
        company_id = user_account.get("company_id")
        api_key = user_account.get("api_key")
        if auth_type == "server_to_server":
            logger.info("auth type is server_to_server")
            bearer_token = generate_access_token(user_account)
        self.client = AdobeClient(
            company_id=company_id,
            api_key=api_key,
            access_token=bearer_token
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
        json_response = self.client.get_reports(
            report_id=self.report_id,
            start_date=self.start_date,
            end_date=self.end_date,
            metrics=self.metrics,
            dimensions=self.dimensions
        )
        logger.info("json_response={}".format(json_response))
        rows = reorder_response(json_response, self.metrics)
        # rows = reorder_response(Mock.JSON_RESPONSE, ['metrics/pageviews','metrics/visits','metrics/visitors'])
        for row in rows:
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
