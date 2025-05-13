from safe_logger import SafeLogger


logger = SafeLogger("adobe pagination", ["password"])
DEFAULT_PAGE_SIZE = 50


class AdobePagination():
    def __init__(self, batch_size=None):
        self.batch_size = batch_size or DEFAULT_PAGE_SIZE
        self.number_of_tries = None
        self.page_offset = None

    def has_next_page(self, response, items_retrieved):
        if response is None:
            logger.info("has_next_page initialisation")
            return True
        try:
            logger.info("decoding json")
            json_response = response.json()
            is_last_page = json_response.get("lastPage", True)
            self.page_offset = json_response.get("number")
            logger.info("is_last_page={}".format(is_last_page))
            return is_last_page
        except Exception:
            return False

    def get_paging_parameters(self, current_params):
        params = {}
        if isinstance(current_params, dict):
            params.update(current_params)
        if isinstance(self.page_offset, int):
            self.page_offset += 1
            params["page"] = self.page_offset
        return params
