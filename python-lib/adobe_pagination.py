from safe_logger import SafeLogger


logger = SafeLogger("adobe pagination", ["password"])
DEFAULT_PAGE_SIZE = 50


class AdobePagination():
    def __init__(self, batch_size=None):
        self.batch_size = batch_size or DEFAULT_PAGE_SIZE
        self.number_of_tries = None
        self.page_offset = None

    def has_next_page(self, response, items_retrieved):
        return False

    def get_paging_parameters(self, current_params):
        return {}
