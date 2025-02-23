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
