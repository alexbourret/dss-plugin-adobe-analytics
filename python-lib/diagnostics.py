from safe_logger import SafeLogger


logger = SafeLogger("plugin diagnostics")


def get_kernel_external_ip():
    logger.info("get_kernel_external_ip")
    try:
        import requests
        response = requests.get("https://api64.ipify.org", params={"format": "json"})
        if response.status_code >= 400:
            logger.error("Error {} trying to check kernel's external ip:{}".format(response.status_code, response.content))
        json_response = response.json()
        kernel_external_ip = json_response.get("ip", "")
        return kernel_external_ip
    except Exception as error:
        logger.error("Could not fetch kernel's remote ip ({})".format(error))
    return ""


def get_kernel_internal_ip():
    target_server = "10.254.254.254"
    logger.info("get_kernel_internal_ip on {}".format(target_server))
    socket_name = ""
    try:
        import socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.connect((target_server, 80))
        socket_name = test_socket.getsockname()[0]
        logger.info("Internal IP is {}".format(socket_name))
        test_socket.close()
    except Exception as error:
        logger.error("get_kernel_internal_ip error : {}".format(error))
    return socket_name


def test_urls():
    import requests
    urls_to_test = [
        {"method": "GET", "url": "https://ims-na1.adobelogin.com/ims/.well-known/openid-configuration"},
        {"method": "POST", "url": "https://ims-na1.adobelogin.com/ims/token/v3"},
        {"method": "GET", "url": "https://analytics.adobe.io/api/"}
    ]
    for url_to_test in urls_to_test:
        url = url_to_test.get("url")
        method = url_to_test.get("method")
        logger.info("trying {} on {}".format(method, url))
        try:
            response = requests.request(method=method, url=url)
            logger.info("status code: {}".format(response.status_code))
            logger.info("answer={}".format(response.content))
        except Exception as error:
            logger.warning("Error {}".format(error))


def decode_jwt(jwt_token):
    try:
        import base64
        import json
        sub_tokens = jwt_token.split('.')
        if len(sub_tokens) < 2:
            logger.error("JWT format is wrong")
            return {}
        token_of_interest = sub_tokens[1]
        padded_token = token_of_interest + "="*divmod(len(token_of_interest), 4)[1]
        decoded_token = base64.urlsafe_b64decode(padded_token.encode('utf-8'))
        json_token = json.loads(decoded_token)
        return json_token
    except Exception as error:
        logger.error("Could not decode JWT token ({})".format(error))
    return {}
