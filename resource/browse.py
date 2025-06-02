from safe_logger import SafeLogger
from adobe_analytics_common import (
    get_connection_from_config
)
from adobe_client import AdobeClient
from dss_selector_choices import DSSSelectorChoices, get_value_from_ui


logger = SafeLogger("adobe-analytics browser", ["bearer_token", "api_key", "client_secret"])
mock = False


def do(payload, config, plugin_config, inputs):
    logger.info("do:payload={}, config={}, plugin_config={}, inputs={}".format(logger.filter_secrets(payload), logger.filter_secrets(config), plugin_config, inputs))
    choices = DSSSelectorChoices()

    try:
        organization_id, company_id, api_key, bearer_token = get_connection_from_config(config, mock=mock)
    except Exception as error:
        logger.error("Error while getting token : {}".format(error))
        return choices.text_message("Error: Please check the logs.")

    logger.info("organization_id={}, company_id={}, api_key={}".format(
            organization_id, company_id, api_key
        )
    )
    parameter_name = payload.get('parameterName')

    if not bearer_token:
        print("ALX:not bearertoken")
        if parameter_name == "report_id":
            return choices.text_message("Set the authentication")
        else:
            return choices.to_dss()

    try:
        client = AdobeClient(
            company_id=company_id,
            api_key=api_key,
            access_token=bearer_token,
            organization_id=organization_id,
            mock=mock
        )
        if parameter_name == "report_id":
            for report_suite in client.next_report_suites():
                label = report_suite.get("name")
                value = report_suite.get("rsid")
                if label and value:
                    choices.append_alphabetically(label, value)
            choices.append_manual_select()
        elif parameter_name == "metrics_ids":
            report_id = get_value_from_ui(payload, "report_id")
            print("listing metrics for rsid '{}'".format(report_id))
            if report_id:
                for metric in client.next_metric(report_id):
                    # Metric's labels are not unique, but multiselect cannot stand that
                    # so the metric ID is added to the label
                    label = "{} - {}".format(metric.get("name"), metric.get("id"))
                    value = metric.get("id")
                    if label and value:
                        choices.append_alphabetically(label, value)
        elif parameter_name == "dimension":
            report_id = get_value_from_ui(payload, "report_id")
            logger.info("listing dimensions for rsid '{}'".format(report_id))
            if report_id:
                for dimension in client.next_dimension(report_id):
                    name = dimension.get("name")
                    extra_title_info = dimension.get("extraTitleInfo")
                    description = dimension.get("description")
                    if extra_title_info:
                        label = "{} - {}".format(name, extra_title_info)
                    elif description:
                        label = "{} ({})".format(name, description)
                    else:
                        label = "{}".format(name)
                    value = dimension.get("id")
                    if label and value:
                        choices.append_alphabetically(label, value)
            choices.append_manual_select()
        elif parameter_name == "segment":
            report_id = get_value_from_ui(payload, "report_id")
            if report_id:
                for segment in client.next_segment(report_id):
                    label = segment.get("name")
                    value = segment.get("id")
                    if label and value:
                        choices.append_alphabetically(label, value)
            choices.append_manual_select()
    except Exception as error:
        logger.error("Error while fetching {} : {}".format(parameter_name, error))
        return choices.text_message("Error: Please check the logs")
    return choices.to_dss()
