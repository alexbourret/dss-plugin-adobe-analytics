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
            logger.info("json_response={}".format(json_response))
            if isinstance(json_response, list):
                # The data return is an array,
                # we can assume this is the only page
                logger.info("response is a list -> no next page")
                return False
            if "error_code" in json_response:
                logger.info("'error_code' in response -> no next page")
                return False
            self.page_offset = json_response.get("number")
            logger.info("page_offset={}".format(self.page_offset))

            is_last_page = json_response.get("lastPage", True)
            logger.info("is_last_page={}".format(is_last_page))
            if is_last_page is True:
                logger.info("lastPage=True in response -> no next page")
                return False
            if "number" in json_response and "totalPages" in json_response:
                total_number_of_pages = json_response.get("totalPages")
                logger.info("total_number_of_pages={}".format(total_number_of_pages))
                if json_response.get("number") >= total_number_of_pages:
                    logger.info("number of pages reached -> no next page")
                    return False
            if self.page_offset > 100:
                logger.warning("failsafe: more that 100 pages -> stopping here")
                return False
            else:
                logger.debug("has next page = true")
                return True
        except Exception as error:
            logger.error("error:{}".format(error))
            return False

    def get_paging_parameters(self, current_params):
        params = {}
        if isinstance(current_params, dict):
            params.update(current_params)
        if isinstance(self.page_offset, int):
            self.page_offset += 1
            params["page"] = self.page_offset
        return params
