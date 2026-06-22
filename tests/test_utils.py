from hcheckz import (
    readiness_point,
    set_ready,
    set_unready,
    del_readiness_point
)

from hcheckz.hcheckz import make_http_response_bytes
from hcheckz.hcheckz import HTTPStatus


def test_httpstatuses():
    assert HTTPStatus.OK.value == (200, "OK")
    assert HTTPStatus.BAD_REQUEST.value == (400, "Bad Request")
    assert HTTPStatus.NOT_FOUND.value == (404, "Not Found")
    assert HTTPStatus.METHOD_NOT_ALLOWED.value == (405, "Method Not Allowed")


def test_make_http_response_bytes():
    bytes = make_http_response_bytes(HTTPStatus.OK)

    assert bytes == (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "Content-Length: 6\r\n"
        "Connection: close\r\n"
        "\r\n"
        "200 OK"
    ).encode('iso-8859-1') 


def test_make_http_response_bytes_with_message():
    bytes = make_http_response_bytes(HTTPStatus.BAD_REQUEST, "testtest")

    assert bytes == (
        "HTTP/1.1 400 Bad Request\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "Content-Length: 25\r\n"
        "Connection: close\r\n"
        "\r\n"
        "400 Bad Request: testtest"
    ).encode('iso-8859-1')