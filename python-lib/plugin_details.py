import json
from dataiku.customrecipe import get_recipe_resource


class PluginDetails(object):
    def __init__(self):
        self.plugin_id, self.plugin_version = get_plugin_details()
        self.beta_version = None
        self.context = get_context_details()

    def get_id(self):
        return self.plugin_id

    def get_version(self):
        return self.plugin_version

    def get_version_with_beta(self):
        if not self.beta_version:
            self.beta_version = get_beta_version()
        if self.beta_version:
            return "{}-{}".format(
                self.plugin_version,
                self.beta_version
            )
        else:
            return self.plugin_version

    def get_context(self):
        return self.context


def get_plugin_details():
    plugin_id = None
    plugin_version = None
    try:
        plugin_json_path = get_plugin_json_path()
        with open(plugin_json_path, 'r') as file:
            stream = file.read()
            plugin_json = json.loads(stream)
            plugin_id = plugin_json.get("id")
            plugin_version = plugin_json.get("version")
    except Exception as error:
        print("Error: could not read plugin details= {}".format(error))
    return plugin_id, plugin_version


def get_beta_version():
    beta_version = None
    try:
        beta_json_path = get_beta_json_path()
        with open(beta_json_path, 'r') as file:
            stream = file.read()
            beta_json = json.loads(stream)
            beta_version = beta_json.get("version")
    except Exception as error:
        print("No plugin beta details: {}".format(error))
    return beta_version


def get_plugin_json_path():
    return get_root_plugin_file_path("plugin.json")


def get_beta_json_path():
    return get_root_plugin_file_path("beta.json")


def get_root_plugin_file_path(file_name):
    resource_path = get_recipe_resource()
    resource_path_tokens = get_token_from_path(resource_path)
    plugin_path_tokens = resource_path_tokens[:-1]
    plugin_path_tokens.append(file_name)
    plugin_json_path = "/".join(plugin_path_tokens)
    return plugin_json_path


def get_token_from_path(path):
    return path.split("/")


def get_context_details():
    import sys
    return sys.version


def get_initialization_string():
    plugin_id, plugin_version = get_plugin_details()
    beta_version = get_beta_version()
    full_version = plugin_version if not beta_version else "{}-beta.{}".format(
        plugin_version, beta_version
    )
    context_details = get_context_details()
    return "Starting plugin {} v{}. Kernel context:{}".format(
        plugin_id, full_version, context_details
    )
