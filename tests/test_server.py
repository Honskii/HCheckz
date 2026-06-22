import asyncio

from json import loads

from hcheckz import *
from hcheckz.hcheckz import _HealthCheck


def test_front():
    assert start_healthchecks == _HealthCheck.start_server


async def send_request(request: bytes, close=False):
    reader, writer = await asyncio.open_connection(
        "127.0.0.1",
        8080
    )
    writer.write(request)
    if close:
        writer.write_eof()
    await writer.drain()
    response = await reader.read()
    writer.close()
    await writer.wait_closed()
    return response


async def test_healthz():
    server_task = await start_healthchecks("127.0.0.1", 8080)

    try:
        if not server_task:
            return

        request = (
            b"GET /healthz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )

        response = await send_request(request)

        assert b"200 OK" in response

    finally:
        await stop_healthchecks()


async def test_readyz():
    server_task = await start_healthchecks("127.0.0.1", 8080)

    try:
        if not server_task:
            raise ValueError


        request = (
            b"GET /readyz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)
        assert b"503 Service Unavailable" in response

        body_str = response.split("\r\n\r\n".encode("iso-8859-1"))[1].decode("iso-8859-1")
        body = loads(body_str)

        assert body == {
            "reason": "Nothing Registred",
        }


        readiness_point("api")
        readiness_point("kafka")
        request = (
            b"GET /readyz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)
        assert b"503 Service Unavailable" in response

        body_str = response.split("\r\n\r\n".encode("iso-8859-1"))[1].decode("iso-8859-1")
        body = loads(body_str)

        assert body == {
            "reason": "Unreadinesses",
            "details": {
                "api": {
                    "code": "Unavailable",
                    "message": "Initialized, ready status was not set"
                },
                "kafka": {
                    "code": "Unavailable",
                    "message": "Initialized, ready status was not set"
                }
            }
        }


        set_ready("api")
        request = (
            b"GET /readyz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)
        assert b"503 Service Unavailable" in response

        body_str = response.split("\r\n\r\n".encode("iso-8859-1"))[1].decode("iso-8859-1")
        body = loads(body_str)

        assert body == {
            "reason": "Unreadinesses",
            "details": {
                "kafka": {
                    "code": "Unavailable",
                    "message": "Initialized, ready status was not set"
                }
            }
        }


        set_ready("kafka")
        request = (
            b"GET /readyz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)
        assert response.count(b"200 OK") == 2

        body = response.split("\r\n\r\n".encode("iso-8859-1"))[1].decode("iso-8859-1")

        assert body == "200 OK"


        set_unready("api", "TEST1", "test1")
        request = (
            b"GET /readyz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)
        assert b"503 Service Unavailable" in response

        body_str = response.split("\r\n\r\n".encode("iso-8859-1"))[1].decode("iso-8859-1")
        body = loads(body_str)

        assert body == {
            "reason": "Unreadinesses",
            "details": {
                "api": {
                    "code": "TEST1",
                    "message": "test1"
                }
            }
        }

        set_unready("kafka", "TEST2", "test2")
        request = (
            b"GET /readyz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)
        assert b"503 Service Unavailable" in response

        body_str = response.split("\r\n\r\n".encode("iso-8859-1"))[1].decode("iso-8859-1")
        body = loads(body_str)

        assert body == {
            "reason": "Unreadinesses",
            "details": {
                "api": {
                    "code": "TEST1",
                    "message": "test1"
                },
                "kafka": {
                    "code": "TEST2",
                    "message": "test2"
                }
            }
        }


    finally:
        await stop_healthchecks()


async def test_stress():
    server_task = await start_healthchecks("127.0.0.1", 8080, timeout=1)

    try:
        if not server_task:
            return

        request = (
            b"GET /healthz1 HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)

        assert b"404 Not Found" in response


        request = (
            b"GET /health1111111111111111111111111111111111111111111111111111"
            b"111111111111111111111111111111111111111111111111111111111111111"
            b"111111111111111111111111111111111111111111111111111111111111111"
            b"111111111111111111111111111111111111111111111111111111111111111"
            b"HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)

        assert b"400 Bad Request: Request line too long" in response


        request = b""
        response = await send_request(request)

        assert b"400 Bad Request: Read timeout" in response


        request = b""
        response = await send_request(request, close=True)

        assert b"400 Bad Request: Empty request" in response

        
        request = b"23111 1223 11111 11111!!! 3%$#2"
        response = await send_request(request, close=True)

        assert b"400 Bad Request: Bad request syntax" in response


        request = (
            b"POST /healthz HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)

        assert b"405 Method Not Allowed: Method POST not allowed" in response


        request = (
            b"GET /healthz MTPROTO/1.2\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)

        assert b"400 Bad Request: Invalid protocol version" in response


        request = (
            "POST /healthz HTTP/1.1\r\n"
        )
        result, error_response = _HealthCheck._parse_request(request, "127.0.0.1") # type: ignore
    
        assert result is None
        assert error_response is not None
        assert b"Parsing error:" in error_response
        assert b"Bad Request: Parsing error:" in error_response


        request = (
            b"POST //google.com HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        response = await send_request(request)

        assert b"302 Found" not in response

    finally:
        await stop_healthchecks()


async def test_server_starts():
    try:
        await start_healthchecks("0.0.0.0", 8000)


        assert await start_healthchecks("0.0.0.0", 8000) is None


        await stop_healthchecks()
        try:
            await start_healthchecks(1.2, 8000) # type: ignore
        except TypeError:
            assert True
        except Exception:
            assert False
        else:
            assert False


        await stop_healthchecks()
        try:
            await start_healthchecks("0.0.0.0", 1.2) # type: ignore
        except TypeError:
            assert True
        except Exception:
            assert False
        else:
            assert False

    finally:
        await stop_healthchecks()