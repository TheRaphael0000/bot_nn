class Command:
    def __init__(self, description, execute_fn):
        self.__description = description
        self.__execute_fn = execute_fn

    def get_description(self):
        return self.__description

    def execute(self, *args, **kwargs):
        return self.__execute_fn(*args, **kwargs)
