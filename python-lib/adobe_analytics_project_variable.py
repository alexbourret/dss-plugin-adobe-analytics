from dataiku import Project


class ProjectVariable():
    def __init__(self, variable_name, variable_type=None, default_value=None):
        self.variable_name = variable_name
        self.project = Project()
        self.variable_type = variable_type or "standard"
        self.default_value = default_value

    def is_not_set(self):
        project_variables = self.project.get_variables()
        project_variable = project_variables.get(self.variable_type, {}).get(self.variable_name)
        if project_variable is None:
            return True
        return False

    def get_value(self):
        project_variables = self.project.get_variables()
        project_variable = project_variables.get(self.variable_type, {}).get(self.variable_name, self.default_value)
        return project_variable

    def set_value(self, value):
        project_variables = self.project.get_variables()
        project_variables[self.variable_type][self.variable_name] = value
        self.project.set_variables(project_variables)
