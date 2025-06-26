from adobe_client import generate_access_token
from safe_logger import SafeLogger


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


def reorder_rows(row_getter, metrics_names):
    output_rows = []
    for item in row_getter:
        if not item:
            continue
        output_row = {}
        output_row['item_id'] = item.get("itemId")
        output_row['item_name'] = item.get("value")
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
