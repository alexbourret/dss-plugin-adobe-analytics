import json
import time

from dataiku.connector import Connector

from adobe_analytics_common import dss_date_to_adobe, get_connection_from_config
from adobe_auth import AdobeAuth
from api_client import APIClient
from dss_selector_choices import get_value_from_ui
from project_variable import ProjectVariable
from records_limit import RecordsLimit
from safe_logger import SafeLogger


logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])
mock = ProjectVariable("dku_adobe-analytics_is-mock", default_value=False).get_value()


def decode_metric_id(metric_dict):
    json_metric = metric_dict
    try:
        json_metric = json.loads(metric_dict)
    except Exception:
        pass

    if isinstance(json_metric, dict):
        metric_name = json_metric.get("name")
        metric_id = json_metric.get("id")
        return metric_name or metric_id, metric_id
    return json_metric, json_metric


def split_csv_values(raw_value):
    if not raw_value or not isinstance(raw_value, str):
        return []
    values = []
    for token in raw_value.split(","):
        stripped = token.strip()
        if stripped:
            values.append(stripped)
    return values


def normalize_metric_id(metric_id):
    if not metric_id or not isinstance(metric_id, str):
        return metric_id
    if metric_id.startswith("metrics/"):
        return metric_id.split("/", 1)[1]
    return metric_id


def normalize_dimension_id(dimension_id):
    if not dimension_id or not isinstance(dimension_id, str):
        return dimension_id
    if not dimension_id.startswith("variables/"):
        return dimension_id

    dimension_value = dimension_id.split("/", 1)[1]
    if dimension_value.startswith("evar"):
        suffix = dimension_value[4:]
        if suffix.isdigit():
            return "eVar{}".format(suffix)
    if dimension_value.startswith("listvar"):
        suffix = dimension_value[7:]
        if suffix.isdigit():
            return "listVar{}".format(suffix)
    return dimension_value


def normalize_date_for_legacy(adobe_date):
    if not adobe_date or not isinstance(adobe_date, str):
        return adobe_date
    return adobe_date.split("T")[0]


class LegacyReportAccumulator(object):
    def __init__(self, metric_names):
        self.metric_names = metric_names
        self.totals = {}

    def add_row(self, row):
        for metric_name in self.metric_names:
            value = row.get(metric_name)
            if value is None:
                continue
            try:
                numeric_value = float(value)
            except Exception:
                continue
            self.totals[metric_name] = self.totals.get(metric_name, 0.0) + numeric_value

    def get_total(self):
        return self.totals


class LegacyAdobeAnalyticsClient(object):
    def __init__(self, api_key, access_token, organization_id, username, password, mock=False):
        if mock:
            logger.warning("Mock mode ! Get mock server started")
            self.report_url = "http://localhost:3001/admin/1.4/rest/"
        else:
            self.report_url = "https://api.omniture.com/admin/1.4/rest/"
        self.client = APIClient(
            server_url=self.report_url,
            auth=AdobeAuth(api_key=api_key, bearer_token=access_token, organization_id=organization_id, username=username, password=username),
            max_number_of_retries=1
        )

    def queue_report(self, report_description):
        response = self.client.post(
            endpoint="",
            url=self.report_url,
            params={"method": "Report.Queue"},
            json={"reportDescription": report_description}
        )
        report_id = response.get("reportID")
        if report_id is None:
            raise Exception("Legacy report queue failed: {}".format(response))
        return report_id

    def get_report(self, report_id):
        return self.client.post(
            endpoint="",
            url=self.report_url,
            params={"method": "Report.Get"},
            json={"reportID": report_id}
        )

    def wait_for_report(self, report_id, max_polls=60, sleep_seconds=2):
        for _ in range(max_polls):
            response = self.get_report(report_id)
            report = response.get("report")
            if report:
                return report

            status = "{}".format(response.get("status", "")).lower()
            error = "{}".format(response.get("error", "")).lower()
            error_desc = "{}".format(response.get("error_description", "")).lower()
            is_still_running = (
                status in ("queued", "running")
                or "not ready" in error
                or "not ready" in error_desc
            )
            if not is_still_running:
                raise Exception("Legacy report retrieval failed: {}".format(response))
            time.sleep(sleep_seconds)
        raise Exception("Timed out while waiting for legacy report {}".format(report_id))


class AdobeAnalyticsLegacyConnector(Connector):
    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        logger.info(
            "Starting legacy connector with config={}".format(
                logger.filter_secrets(config)
            )
        )

        self.report_id = get_value_from_ui(config, "report_id")
        if not self.report_id:
            raise Exception("A valid Report Suite ID needs to be set")

        is_date_entered_manually = config.get("is_date_entered_manually", False)
        if not is_date_entered_manually:
            start_date = dss_date_to_adobe(config.get("start_date"))
            end_date = dss_date_to_adobe(config.get("end_date"))
        else:
            start_date = config.get("manual_start_date")
            end_date = config.get("manual_end_date")

        self.start_date = normalize_date_for_legacy(start_date)
        self.end_date = normalize_date_for_legacy(end_date)
        if not self.start_date or not self.end_date:
            raise Exception("A valid date range must be set")

        metrics_ids = config.get("metrics_ids", [])
        self.metric_names = []
        self.metrics = []
        for metric_dict in metrics_ids:
            metric_name, metric_id = decode_metric_id(metric_dict)
            normalized_metric_id = normalize_metric_id(metric_id)
            if not normalized_metric_id:
                continue
            self.metric_names.append(metric_name or normalized_metric_id)
            self.metrics.append({"id": normalized_metric_id})
        if not self.metrics:
            raise Exception("At least one metric must be selected")

        dimensions_from_selector = config.get("dimensions_ids", []) or []
        dimensions_from_manual = split_csv_values(config.get("dimensions_manual", ""))
        ordered_dimensions = []
        for dimension_id in list(dimensions_from_selector) + list(dimensions_from_manual):
            normalized_dimension_id = normalize_dimension_id(dimension_id)
            if normalized_dimension_id and normalized_dimension_id not in ordered_dimensions:
                ordered_dimensions.append(normalized_dimension_id)
        if not ordered_dimensions:
            raise Exception("At least one dimension must be selected")
        self.dimension_ids = ordered_dimensions

        self.dimension_column_names = []
        for index, _ in enumerate(self.dimension_ids):
            self.dimension_column_names.append("dimension_{}".format(index + 1))

        self.segment = get_value_from_ui(self.config, "segment")
        self.shoud_add_total_row = config.get("shoud_add_total_row", False)
        self.shoud_add_date_column = config.get("shoud_add_date_column", False)
        self.max_rows_per_dimension = int(config.get("max_rows_per_dimension", 50000))

        organization_id, company_id, api_key, bearer_token, username, password = get_connection_from_config(config, mock=mock)
        if not api_key or not bearer_token:
            raise Exception("Authentication is invalid. Please check the selected preset.")

        self.client = LegacyAdobeAnalyticsClient(
            api_key=api_key,
            access_token=bearer_token,
            organization_id=organization_id,
            username=username,
            password=password,
            mock=mock
        )

    def get_read_schema(self):
        return None

    def _build_report_description(self):
        elements = []
        for dimension_id in self.dimension_ids:
            elements.append({
                "id": dimension_id,
                "top": self.max_rows_per_dimension
            })

        description = {
            "reportSuiteID": self.report_id,
            "dateFrom": self.start_date,
            "dateTo": self.end_date,
            "metrics": self.metrics,
            "elements": elements
        }
        if self.segment:
            description["segments"] = [{"id": self.segment}]
        return description

    def _flatten_rows(self, report_rows):
        def recurse(rows, depth, dimension_values):
            if not isinstance(rows, list):
                return
            for row in rows:
                current_values = list(dimension_values)
                current_values.append(row.get("name"))
                breakdown = row.get("breakdown")
                is_leaf = not isinstance(breakdown, list) or len(breakdown) == 0 or depth >= len(self.dimension_ids) - 1
                if is_leaf:
                    output_row = {}
                    for index, column_name in enumerate(self.dimension_column_names):
                        output_row[column_name] = current_values[index] if index < len(current_values) else None
                    for metric_name, metric_value in zip(self.metric_names, row.get("counts", [])):
                        output_row[metric_name] = metric_value
                    yield output_row
                else:
                    for nested_row in recurse(breakdown, depth + 1, current_values):
                        yield nested_row

        for output in recurse(report_rows, 0, []):
            yield output

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        accumulator = LegacyReportAccumulator(self.metric_names)

        report_description = self._build_report_description()
        logger.info("legacy reportDescription={}".format(report_description))

        report_id = self.client.queue_report(report_description)
        report = self.client.wait_for_report(report_id)
        data = report.get("data", [])

        for row in self._flatten_rows(data):
            if self.shoud_add_total_row:
                accumulator.add_row(row)
            if self.shoud_add_date_column:
                row["Date"] = self.start_date
            yield row
            if limit.is_reached():
                return

        if self.shoud_add_total_row:
            total_row = {}
            for column_name in self.dimension_column_names:
                total_row[column_name] = None
            if self.dimension_column_names:
                total_row[self.dimension_column_names[0]] = "Total"
            total_row.update(accumulator.get_total())
            if self.shoud_add_date_column:
                total_row["Date"] = self.start_date
            yield total_row

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
