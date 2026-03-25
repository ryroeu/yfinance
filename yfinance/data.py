"""HTTP session and request orchestration for Yahoo Finance data access."""

import functools
import socket
import threading
import time as _time
from functools import lru_cache


from curl_cffi import requests
from frozendict import frozendict

from . import utils
from .auth import YahooAuthMixin
from .config import YF_CONFIG as YfConfig
from .exceptions import YFException, YFRateLimitError


def _is_transient_error(exception):
    """Check if error is transient (network/timeout) and should be retried."""
    if isinstance(exception, (TimeoutError, socket.error, OSError)):
        return True
    error_type_name = type(exception).__name__
    transient_error_types = {
        "Timeout",
        "TimeoutError",
        "ConnectionError",
        "ConnectTimeout",
        "ReadTimeout",
        "ChunkedEncodingError",
        "RemoteDisconnected",
    }
    return error_type_name in transient_error_types


CACHE_MAXSIZE = 64


def lru_cache_freezeargs(func):
    """
    Decorator transforms mutable dictionary and list arguments into immutable types
    Needed so lru_cache can cache method calls what has dict or list arguments.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        args = tuple(frozendict(arg) if isinstance(arg, dict) else arg for arg in args)
        kwargs = {
            k: frozendict(v) if isinstance(v, dict) else v for k, v in kwargs.items()
        }
        args = tuple(tuple(arg) if isinstance(arg, list) else arg for arg in args)
        kwargs = {k: tuple(v) if isinstance(v, list) else v for k, v in kwargs.items()}
        return func(*args, **kwargs)

    # copy over the lru_cache extra methods to this wrapper to be able to access them
    # after this decorator has been applied
    setattr(wrapped, "cache_info", getattr(func, "cache_info"))
    setattr(wrapped, "cache_clear", getattr(func, "cache_clear"))
    return wrapped


class SingletonMeta(type):
    """
    Metaclass that creates a Singleton instance.
    """

    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            else:
                # Update the existing instance
                if "session" in kwargs or (args and len(args) > 0):
                    session = kwargs.get("session") if "session" in kwargs else args[0]
                    cls._instances[cls]._set_session(session)
            return cls._instances[cls]


class YfData(YahooAuthMixin, metaclass=SingletonMeta):
    """
    Have one place to retrieve data from Yahoo API in order to ease caching and speed up operations.
    Singleton means one session one cookie shared by all threads.
    """

    def __init__(self, session=None):
        self._init_auth(session)

    @utils.log_indent_decorator
    def get(self, url, params=None, timeout=30):
        """Perform an HTTP GET request with cookie and crumb handling."""
        request_config = {"url": url, "params": params, "timeout": timeout}
        response = self._make_request(self._session.get, request_config)
        if self._is_this_consent_url(response.url):
            return self._accept_consent_form(response, timeout)
        return response

    def _normalize_post_args(self, args, kwargs):
        kwargs_copy = dict(kwargs)
        has_body_kwarg = "body" in kwargs_copy
        has_params_kwarg = "params" in kwargs_copy
        has_timeout_kwarg = "timeout" in kwargs_copy
        has_data_kwarg = "data" in kwargs_copy

        body = kwargs_copy.pop("body", None)
        params = kwargs_copy.pop("params", None)
        timeout = kwargs_copy.pop("timeout", 30)
        data = kwargs_copy.pop("data", None)

        if len(args) > 4:
            raise TypeError("post() takes at most 5 positional arguments")
        if len(args) >= 1:
            if has_body_kwarg:
                raise TypeError("post() got multiple values for argument 'body'")
            body = args[0]
        if len(args) >= 2:
            if has_params_kwarg:
                raise TypeError("post() got multiple values for argument 'params'")
            params = args[1]
        if len(args) >= 3:
            if has_timeout_kwarg:
                raise TypeError("post() got multiple values for argument 'timeout'")
            timeout = args[2]
        if len(args) == 4:
            if has_data_kwarg:
                raise TypeError("post() got multiple values for argument 'data'")
            data = args[3]
        if kwargs_copy:
            unexpected = ", ".join(sorted(kwargs_copy))
            raise TypeError(f"post() got unexpected keyword arguments: {unexpected}")
        return body, params, timeout, data

    @utils.log_indent_decorator
    def post(self, url, *args, **kwargs):
        """Perform an HTTP POST request with cookie and crumb handling."""
        body, params, timeout, data = self._normalize_post_args(args, kwargs)
        request_config = {
            "url": url,
            "body": body,
            "params": params,
            "timeout": timeout,
            "data": data,
        }
        return self._make_request(self._session.post, request_config)

    def _log_request_details(self, url, params):
        if len(url) > 200:
            utils.get_yf_logger().debug("url=%s...", url[:200])
        else:
            utils.get_yf_logger().debug("url=%s", url)
        utils.get_yf_logger().debug("params=%s", params)

    def _build_request_args(self, request_config):
        url = request_config["url"]
        params = request_config.get("params")
        timeout = request_config.get("timeout", 30)
        body = request_config.get("body")
        data = request_config.get("data")

        if params is None:
            params = {}
        if "crumb" in params:
            raise YFException(
                "Don't manually add 'crumb' to params dict, let data.py handle it"
            )

        crumb, strategy = self._get_cookie_and_crumb(timeout)
        crumbs = {"crumb": crumb} if crumb is not None else {}
        request_args = {"url": url, "params": {**params, **crumbs}, "timeout": timeout}
        if body:
            request_args["json"] = body
        if data:
            request_args["data"] = data
            request_args["headers"] = {"Content-Type": "application/json"}
        return request_args, strategy

    def _request_with_retry(self, request_method, request_args):
        retryable_exceptions = (
            requests.exceptions.RequestException,
            TimeoutError,
            socket.error,
            OSError,
        )
        for attempt in range(YfConfig.network.retries + 1):
            try:
                return request_method(**request_args)
            except retryable_exceptions as exc:
                if _is_transient_error(exc) and attempt < YfConfig.network.retries:
                    _time.sleep(2**attempt)
                    continue
                raise
        raise RuntimeError("Unreachable retry loop termination")

    def _retry_with_alternate_cookie_strategy(
        self, request_method, request_args, strategy, timeout
    ):
        self._set_cookie_strategy("csrf" if strategy == "basic" else "basic")
        crumb, _ = self._get_cookie_and_crumb(timeout)
        if crumb is not None:
            request_args["params"]["crumb"] = crumb
        else:
            request_args["params"].pop("crumb", None)

        response = request_method(**request_args)
        utils.get_yf_logger().debug("response code=%s", response.status_code)
        if response.status_code == 429:
            raise YFRateLimitError()
        return response

    @utils.log_indent_decorator
    def _make_request(self, request_method, request_config):
        """Execute a request and retry with fallback cookie strategy when needed."""
        self._log_request_details(request_config["url"], request_config.get("params"))
        request_args, strategy = self._build_request_args(request_config)
        request_args.update(self._get_network_request_options())
        response = self._request_with_retry(request_method, request_args)
        utils.get_yf_logger().debug("response code=%s", response.status_code)
        if response.status_code >= 400:
            timeout = request_config.get("timeout", 30)
            response = self._retry_with_alternate_cookie_strategy(
                request_method, request_args, strategy, timeout
            )
        return response

    @lru_cache_freezeargs
    @lru_cache(maxsize=CACHE_MAXSIZE)
    def cache_get(self, url, params=None, timeout=30):
        """Return cached GET responses for immutable argument combinations."""
        return self.get(url, params, timeout)

    def get_raw_json(self, url, params=None, timeout=30):
        """Fetch JSON payload and raise for HTTP errors."""
        utils.get_yf_logger().debug("get_raw_json(): %s", url)
        response = self.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
