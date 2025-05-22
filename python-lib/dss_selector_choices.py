class DSSSelectorChoices(object):
    def __init__(self):
        self.choices = []

    def append(self, label, value):
        self.choices.append(
            {
                "label": label,
                "value": value
            }
        )

    def append_alphabetically(self, new_label, new_value):
        index = 0
        new_choice = {
            "label": new_label,
            "value": new_value
        }
        for choice in self.choices:
            choice_label = choice.get("label")
            if choice_label.lower() < new_label.lower():
                index += 1
            else:
                break
        self.choices.insert(index, new_choice)

    def append_manual_select(self):
        self.choices.append(
            {
                "label": "✍️ Enter manually",
                "value": "_dku_manual_select"
            }
        )

    def _build_select_choices(self, choices=None):
        if not choices:
            return {"choices": []}
        if isinstance(choices, str):
            return {"choices": [{"label": "{}".format(choices)}]}
        if isinstance(choices, list):
            return {"choices": choices}
        if isinstance(choices, dict):
            returned_choices = []
            for choice_key in choices:
                returned_choices.append({
                    "label": choice_key,
                    "value": choices.get(choice_key)
                })
            return {"choices": returned_choices}

    def text_message(self, text_message):
        return self._build_select_choices(text_message)

    def to_dss(self):
        return self._build_select_choices(self.choices)


def get_value_from_ui(config, key_name):
    if "rootModel" in config:
        root_model = config.get("rootModel", {})
    else:
        root_model = config
    value = root_model.get(key_name)
    if value == "_dku_manual_select":
        value = root_model.get("{}_manual".format(key_name))
    return value
