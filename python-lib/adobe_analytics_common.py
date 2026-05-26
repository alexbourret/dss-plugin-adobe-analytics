from adobe_client import generate_access_token
from safe_logger import SafeLogger
from datetime import datetime, timedelta


logger = SafeLogger("adobe-analytics plugin", ["bearer_token", "api_key", "client_secret"])


def reorder_response(json_response, metrics_names):
    output_rows = []
    rows = json_response.get("rows", [])
    for item in rows:
        output_row = {}
        output_row['item_id'] = item.get("itemId")
        output_row['item_name'] = item.get("value")
        item_data = item.get("data", [])
        for metric_name, metric_value in zip(metrics_names, item_data):
            output_row[metric_name] = metric_value
        output_rows.append(output_row)
    return output_rows


def reorder_rows(row_getter, metrics_names, item_name=None, item_id_column_name=None):
    item_name = item_name or "item_name"
    item_id_column_name = item_id_column_name or "item_id"
    output_rows = []
    for item in row_getter:
        if not item:
            continue
        output_row = {}
        output_row[item_id_column_name] = item.get("itemId")
        output_row[item_name] = item.get("value")
        item_data = item.get("data", [])
        for metric_name, metric_value in zip(metrics_names, item_data):
            output_row[metric_name] = metric_value
        output_rows.append(output_row)
    for output_row in output_rows:
        yield output_row


def get_connection_from_config(config, mock=False):
    auth_type = config.get("auth_type", "user_account")
    logger.info("auth_type={}".format(auth_type))
    user_account = config.get(auth_type, {})
    bearer_token = user_account.get("bearer_token")
    organization_id = user_account.get("organization_id")
    company_id = user_account.get("company_id")
    api_key = user_account.get("api_key")
    if auth_type == "server_to_server" and user_account:
        logger.info("auth type is server_to_server")
        bearer_token = generate_access_token(user_account, mock=mock)
        api_key = user_account.get("client_id")
    return organization_id, company_id, api_key, bearer_token


def dss_date_to_adobe(dss_date):
    if not dss_date or not isinstance(dss_date, str):
        return None
    if dss_date.endswith("Z"):
        return dss_date[:-1]


def get_date_range(config):
    #  output format should be 2024-12-31T23:59:00.000
    date_range = config.get("date_range", None)  # Custom by default
    if date_range is None:  # not is_date_entered_manually:
        start_date = dss_date_to_adobe(config.get("start_date"))
        end_date = dss_date_to_adobe(config.get("end_date"))
    elif date_range == "manual":
        start_date = config.get("manual_start_date")
        end_date = config.get("manual_end_date")
    elif date_range == "today":
        today = datetime.now() - timedelta(days=0)
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = today.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "yesterday":
        yesterday = datetime.now() - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = yesterday.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "last_7_days":
        today = datetime.now()
        start_day = today - timedelta(days=7)
        end_day = today - timedelta(days=1)
        start_date = start_day.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = end_day.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "last_14_days":
        today = datetime.now()
        start_day = today - timedelta(days=14)
        end_day = today - timedelta(days=1)
        start_date = start_day.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = end_day.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "last_week":
        today = datetime.now()
        current_monday = today - timedelta(days=today.weekday())
        last_monday = current_monday - timedelta(days=7)
        last_friday = last_monday + timedelta(days=4)
        start_date = last_monday.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = last_friday.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "last_30_days":
        today = datetime.now()
        start_day = today - timedelta(days=30)
        end_day = today - timedelta(days=1)
        start_date = start_day.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = end_day.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "last_60_days":
        today = datetime.now()
        start_day = today - timedelta(days=60)
        end_day = today - timedelta(days=1)
        start_date = start_day.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = end_day.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "last_month":
        today = datetime.now()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        start_date = first_day_last_month.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
        end_date = last_day_last_month.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000")
    elif date_range == "last_quarter":
        today = datetime.now()
        current_quarter = (today.month - 1) // 3 + 1
        current_year = today.year
        if current_quarter == 1:
            last_quarter = 4
            year_of_last_quarter = current_year - 1
        else:
            last_quarter = current_quarter - 1
            year_of_last_quarter = current_year
        start_month = (last_quarter - 1) * 3 + 1
        end_month = start_month + 2
        start_date = datetime(year_of_last_quarter, start_month, 1, 0, 0, 0).strftime("%Y-%m-%dT%H:%M:%S.000")
        if end_month == 12:
            end_date_dt = datetime(year_of_last_quarter, 12, 31, 23, 59, 0)
        else:
            first_day_after_quarter = datetime(year_of_last_quarter, end_month + 1, 1)
            end_date_dt = first_day_after_quarter - timedelta(days=1)
            end_date_dt = end_date_dt.replace(hour=23, minute=59, second=0, microsecond=0)
        end_date = end_date_dt.strftime("%Y-%m-%dT%H:%M:%S.000")
    return start_date, end_date
