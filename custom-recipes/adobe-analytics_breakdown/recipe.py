import ast
import json
import re

import dataiku
import pandas as pd
from dataiku.customrecipe import get_input_names_for_role, get_output_names_for_role, get_recipe_config

from adobe_analytics_common import get_connection_from_config, reorder_rows
from adobe_client import AdobeClient
from dss_selector_choices import get_value_from_ui
from project_variable import ProjectVariable
from safe_logger import SafeLogger
from adobe_accumulator import Accumulator


logger = SafeLogger("adobe-analytics breakdown recipe", ["bearer_token", "api_key", "client_secret"])
mock = ProjectVariable("dku_adobe-analytics_is-mock", default_value=False).get_value()
dimension_pattern = re.compile(r"^dimension_(\d+)$")


def normalize_value(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def parse_json_like(value):
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return json.loads(stripped)
        except Exception:
            pass
        try:
            return ast.literal_eval(stripped)
        except Exception:
            pass
    return None


def decode_metrics(value):
    parsed = parse_json_like(value)
    if not isinstance(parsed, list):
        raise Exception(
            "Could not decode 'metrics' from input dataset. "
            "Enable 'Add a breakdown column' on the source Adobe dataset."
        )

    metrics = []
    metric_names = []
    for index, metric in enumerate(parsed):
        if isinstance(metric, dict):
            metric_id = metric.get("id")
            metric_name = metric.get("name") or metric_id
            column_id = metric.get("columnId")
        else:
            metric_id = metric
            metric_name = metric
            column_id = None

        if not metric_id:
            raise Exception("Metric definition is invalid in input dataset: {}".format(metric))

        if column_id is None:
            column_id = "{}".format(index)

        metrics.append({
            "columnId": "{}".format(column_id),
            "id": metric_id
        })
        metric_names.append(metric_name)
    return metrics, metric_names


def extract_dimension_map(row):
    dimensions = {}
    for key, value in row.items():
        match = dimension_pattern.match(key)
        if match:
            dimensions[int(match.group(1))] = normalize_value(value)
    if len(dimensions) == 0 and "dimension" in row:
        # Backward compatibility with datasets created before dimension_1 naming.
        dimensions[1] = normalize_value(row.get("dimension"))
    return dimensions


def build_output_row(
        source_row,
        breakdown_row,
        dimension_map,
        next_dimension_column,
        breakdown_dimension,
        keep_source_columns
):
    output_row = {}
    if keep_source_columns:
        for key, value in source_row.items():
            output_row[key] = normalize_value(value)

    for dimension_index in sorted(dimension_map.keys()):
        output_row["dimension_{}".format(dimension_index)] = dimension_map.get(dimension_index)
    output_row[next_dimension_column] = breakdown_dimension

    output_row["item_id"] = breakdown_row.get("item_id")
    output_row["item_name"] = breakdown_row.get("item_name")
    output_row["source_item_id"] = normalize_value(source_row.get("item_id"))
    output_row["source_item_name"] = normalize_value(source_row.get("item_name"))

    for key, value in breakdown_row.items():
        if key in ("item_id", "item_name"):
            continue
        output_row[key] = value

    return output_row


def sort_dimension_columns(columns):
    dimension_columns = []
    for column in columns:
        match = dimension_pattern.match(column)
        if match:
            dimension_columns.append((int(match.group(1)), column))
    dimension_columns.sort(key=lambda item: item[0])
    return [column for _, column in dimension_columns]


def reorder_output_columns(output_df, metric_names):
    if output_df.empty:
        return output_df
    columns = list(output_df.columns)
    ordered_dimension_columns = sort_dimension_columns(columns)

    preferred_columns = ["item_id"]
    preferred_columns.extend(ordered_dimension_columns)
    preferred_columns.extend([
        "item_name",
        "source_item_id",
        "source_item_name"
    ])
    preferred_columns.extend(metric_names or [])
    preferred_columns.extend([
        "report_id",
        "start_date",
        "end_date",
        "metrics",
        "segment",
        "Date"
    ])

    final_columns = []
    for column in preferred_columns:
        if column in output_df.columns and column not in final_columns:
            final_columns.append(column)

    remaining_columns = sorted([column for column in columns if column not in final_columns])
    final_columns.extend(remaining_columns)
    return output_df.reindex(columns=final_columns)


def filter_total_row(total_row, last_row, column_name):
    filtered_total_row = total_row.copy()
    filtered_total_row["item_id"] = None
    filtered_total_row["item_name"] = column_name
    for key in filtered_total_row:
        if key.startswith("dimension_"):
            filtered_total_row[key] = last_row.get(key)
        if key in ["report_id", "start_date", "end_date", "source_item_id", "source_item_name"]:
            filtered_total_row[key] = last_row.get(key)
        if key in ["metrics", "segment", "Date"]:
            filtered_total_row[key] = None
    return filtered_total_row


def main():
    config = get_recipe_config()
    input_name = get_input_names_for_role("input_dataset")[0]
    output_name = get_output_names_for_role("output_dataset")[0]
    breakdown_dimension = get_value_from_ui(config, "dimension")
    keep_source_columns = config.get("keep_source_columns", True)
    should_add_total_row = config.get("should_add_total_row", False)

    logger.info(
        "Starting plugin adobe-analytics breakdown dimension recipe v0.0.23 with config={}".format(
            logger.filter_secrets(config)
        )
    )

    if not breakdown_dimension:
        raise Exception("Please select a breakdown dimension")

    input_dataset = dataiku.Dataset(input_name)
    input_df = input_dataset.get_dataframe(infer_with_pandas=False)

    if input_df.empty:
        logger.warning("Input dataset is empty, writing an empty output")
        dataiku.Dataset(output_name).write_with_schema(pd.DataFrame())
        return

    first_row = input_df.iloc[0].to_dict()
    report_id = normalize_value(first_row.get("report_id"))
    start_date = normalize_value(first_row.get("start_date"))
    end_date = normalize_value(first_row.get("end_date"))
    dimension_map = extract_dimension_map(first_row)
    segment = normalize_value(first_row.get("segment"))

    if not report_id or not start_date or not end_date:
        raise Exception(
            "Input dataset is missing one of report_id/start_date/end_date. "
            "Use an Adobe 'Get Reports' dataset with 'Add a breakdown column' enabled."
        )

    if len(dimension_map) == 0:
        raise Exception(
            "Input dataset is missing dimension metadata. "
            "Use an Adobe dataset with dimension_1 (or legacy dimension) column."
        )
    max_dimension_index = max(dimension_map.keys())
    source_dimension = dimension_map.get(max_dimension_index)
    next_dimension_column = "dimension_{}".format(max_dimension_index + 1)
    if not source_dimension:
        raise Exception(
            "Could not resolve source dimension from column dimension_{}.".format(max_dimension_index)
        )

    metrics, metric_names = decode_metrics(first_row.get("metrics"))

    organization_id, company_id, api_key, bearer_token = get_connection_from_config(config, mock=mock)
    if not bearer_token:
        raise Exception("Missing bearer token. Check your authentication preset.")

    client = AdobeClient(
        company_id=company_id,
        api_key=api_key,
        access_token=bearer_token,
        organization_id=organization_id,
        mock=mock
    )

    output_rows = []
    if should_add_total_row:
        grand_total = Accumulator()
    for _, source_row in input_df.iterrows():
        source_row_dict = source_row.to_dict()
        source_item_id = normalize_value(source_row_dict.get("item_id"))
        if not source_item_id:
            continue
        if should_add_total_row:
            input_row_total = Accumulator()

        for breakdown_row in reorder_rows(
            client.next_breakdown_row(
                report_id=report_id,
                start_date=start_date,
                end_date=end_date,
                metrics=metrics,
                source_dimension=source_dimension,
                source_item_id=source_item_id,
                breakdown_dimension=breakdown_dimension,
                segment=segment
            ),
            metric_names
        ):
            output_row = build_output_row(
                source_row=source_row_dict,
                breakdown_row=breakdown_row,
                dimension_map=dimension_map,
                next_dimension_column=next_dimension_column,
                breakdown_dimension=breakdown_dimension,
                keep_source_columns=keep_source_columns
            )
            output_rows.append(
                output_row
            )
            if should_add_total_row:
                input_row_total.add_row(output_row)
                grand_total.add_row(output_row)
        if should_add_total_row:
            total_row = input_row_total.get_total()
            total_row = filter_total_row(total_row, output_row, "Total")
            output_rows.append(total_row)
    if should_add_total_row:
        total_row = grand_total.get_total()
        total_row = filter_total_row(total_row, output_row, "Grand Total")
        total_row["source_item_id"] = None
        total_row["source_item_name"] = None
        output_rows.append(total_row)

    output_dataset = dataiku.Dataset(output_name)
    if len(output_rows) == 0:
        logger.warning("No breakdown row returned by Adobe")
        output_dataset.write_with_schema(pd.DataFrame())
        return

    output_df = pd.DataFrame(output_rows)
    output_df = reorder_output_columns(output_df, metric_names)
    output_dataset.write_with_schema(output_df)


main()
