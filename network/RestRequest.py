from model import Resource
import requests
import base64
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

HTTP_VERBS = ['delete', 'get', 'head', 'options', 'patch', 'post', 'put',
              'trace']

HTTP_STATUS_OK = 200
HTTP_STATUS_CREATED = 201
HTTP_STATUS_NO_CONTENT = 204

HTTP_HEADER_ACCEPT = 'accept'
HTTP_HEADER_CONTENT_TYPE = 'content-type'


class RestRequest:
    def __init__(self, href):
        """
        Initialize REST request
        :param href: the request href
        """
        self.href = href
        self.verb = None
        self.user = None
        self.pwd = None

        self.params = None
        self.data = None
        self.files = None

        self.accept_type = None
        self.content_type = None

    def __call__(self, data=None, files=None, params=None):
        """
        Make RestRequest callable
        :param data: data in request
        :param files: files as contents
        :param params: URL parameters
        :return:
        """
        self.data = data
        self.files = files
        self.params = params
        return self.request()

    def auth(self, user, pwd):
        """
        Fill authentication in request
        :param user: user name
        :param pwd: user password
        :return: RestRequest instance
        """
        self.user = user
        self.pwd = pwd
        return self

    def accept(self, media_type):
        """
        Fill HTTP header accept
        :param media_type: media type of HTTP header accept
        :return: RestRequest instance
        """
        self.accept_type = media_type
        return self

    def as_(self, media_type):
        """
        Fill HTTP header content-type
        :param media_type: media type of HTTP header content-type
        :return: RestRequest instance
        """
        self.content_type = media_type
        return self

    def __getattr__(self, name):
        """
        Populate callable method name if it is HTTP method
        :param name: callable method name
        :return: RestRequest instance
        """
        if self._is_verb(name):
            self.verb = name
            return self
        else:
            raise AttributeError(name)

    def prepare_headers(self):
        """
        Prepare HTTP headers
        :return:
        """
        headers = self.get_basic_authn_header()

        if hasattr(self, 'content_type'):
            headers.update(self._get_content_header())

        if hasattr(self, 'accept_type'):
            headers.update(self._get_accept_header())
        return headers

    def request(self):
        """
        Run request
        :return:
        """
        logger.debug('    [%s <--> URI %s]' % (self.verb.upper(), self.href))
        headers = self.prepare_headers()

        if self._is_multipart_request():
            rsp = requests.request(self.verb, self.href, headers=headers, params=self.params, files=self.files)
        else:
            rsp = requests.request(self.verb, self.href, headers=headers, params=self.params, data=self.data)

        self.check_return_code(rsp)
        return RestResponse(rsp)

    def get_basic_authn_header(self):
        """
        Get basic authentication HTTP header
        :return:
        """
        if not self.user or not self.pwd:
            raise ValueError('login name or password is invalid.')

        encoded_credential = base64.b64encode((self.user + ":" + self.pwd).encode("utf-8"))
        return {"Authorization": "Basic " + encoded_credential.decode("utf-8")}

    def _get_content_header(self):
        """
        Get HTTP content-type header
        :return: content-type header
        """
        if self._is_multipart_request():
            return {}

        if hasattr(self, 'content_type'):
            return {HTTP_HEADER_CONTENT_TYPE: self.content_type}

        return {}

    def _is_multipart_request(self):
        """
        Check if the request is multipart
        :return:
        """
        if self.files:
            return True
        else:
            return False

    def _get_accept_header(self):
        """
        Get HTTP header accept
        :return:
        """
        return {HTTP_HEADER_ACCEPT: self.accept_type}

    @staticmethod
    def _is_verb(name):
        """
        Check if the name is HTTP verb
        :param name:
        :return:
        """
        return name in HTTP_VERBS

    def check_return_code(self, response):
        """
        Check HTTP response code
        :param response:
        :return:
        """
        code = response.status_code
        logger.debug('    [Status code: %s]', str(code))

        if self.verb == 'get' and not code == HTTP_STATUS_OK:
            self._dump_error_info()
            raise Exception(response.content)

        if self.verb == 'post' and not code == HTTP_STATUS_OK and not code == HTTP_STATUS_CREATED:
            self._dump_error_info()
            raise Exception(response.content)

        if self.verb == 'delete' and not code == HTTP_STATUS_NO_CONTENT:
            self._dump_error_info()
            raise Exception(response.content)

        logger.debug('    [Succeed]\n')

    def _dump_error_info(self):
        logger.error('Exception caught during %s for link %s' % (self.verb, self.href))


class RestResponse:
    def __init__(self, response):
        """
        REST response
        :param response: HTTP response
        """
        self.response = response

    def resource(self):
        """
        Get the resource from HTTP response
        :return:
        """
        if len(self.response.content) is not 0:
            resource = Resource.Resource(self.response.json())
            return resource
        else:
            return None

    def status(self):
        """
        Get response code of REST response
        :return:
        """
        return self.response.status_code
