import asyncio

from dataclasses import dataclass
from enum import Enum
from functools import partial
from logging import getLogger
from typing import List, Dict, Optional
from json import dumps


log = getLogger(__name__)

@dataclass(slots=True)
class ParsedRequest:
    method: str
    path: str
    version: str
    client_ip: str

class HTTPStatus(Enum):
    OK = (200, "OK")
    BAD_REQUEST = (400, "Bad Request")
    NOT_FOUND = (404, "Not Found")
    METHOD_NOT_ALLOWED = (405, "Method Not Allowed")

def make_http_response_bytes(
    status: HTTPStatus,
    message: Optional[str] = None
) -> bytes:
    code, text = status.value
    body = f"{code} {text}{': ' + message if message else ''}".encode("utf-8")
    headers = (
        f"HTTP/1.1 {code} {text}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode('iso-8859-1')
    return headers + body

class _Manager:
    _readiness_points: Dict[str, Optional[Dict[str, str]]] = {}

    @classmethod
    def get_unreadinesses(cls) -> dict:
        return dict(filter(lambda kv: kv[1], cls._readiness_points.items()))

    @classmethod
    def get_readiness_points(cls) -> List[str]:
        return list(cls._readiness_points.keys())

    @classmethod
    def readiness_point(cls, name: str) -> None:
        if not isinstance(name, str):
            exception_message = f"Name argument must be string (not {type(name)}) type"
            log.error(exception_message)
            raise TypeError(exception_message)
        cls._readiness_points[name] = {
            "code": "Unavailable",
            "message": "Initialized, ready status was not set"
        }
        log.info(f"Created point of readiness at {name}")

    @classmethod
    def delete_readiness_point(cls, name: str) -> None:
        if not isinstance(name, str):
            exception_message = f"Name argument must be string (not {type(name)}) type"
            log.error(exception_message)
            raise TypeError(exception_message)
        if name not in cls._readiness_points:
            exception_message = f"Unknown readiness point '{name}'"
            log.error(exception_message)
            raise KeyError(exception_message)
        del cls._readiness_points[name]

    @classmethod
    def set_unready(cls, name: str, code: str, message: str) -> None:
        if not isinstance(name, str):
            exception_message = f"'name' argument must be string (not {type(name)}) type"
            log.error(exception_message)
            raise TypeError(exception_message)
        if not isinstance(code, str):
            exception_message = f"'code' argument must be string (not {type(code)}) type"
            log.error(exception_message)
            raise TypeError(exception_message)
        if not isinstance(message, str):
            exception_message = f"'message' argument must be string (not {type(message)}) type"
            log.error(exception_message)
            raise TypeError(exception_message)
        if name not in cls._readiness_points:
            exception_message = f"Unknown readiness point '{name}'"
            log.error(exception_message)
            raise KeyError(exception_message)
        cls._readiness_points[name] = {
            "code": code,
            "message": message
        }

    @classmethod
    def set_ready(cls, name: str) -> None:
        if not isinstance(name, str):
            exception_message = f"'name' argument must be string (not {type(name)}) type"
            log.error(exception_message)
            raise TypeError(exception_message)
        if name not in cls._readiness_points:
            exception_message = f"Unknown readiness point '{name}'"
            log.error(exception_message)
            raise KeyError(exception_message)
        cls._readiness_points[name] = dict()

class _HealthCheck:
    is_server_active: bool = False
    manager = _Manager

    @staticmethod
    def _parse_request(
        raw_line: bytes, 
        client_ip: str
    ) -> tuple[Optional[ParsedRequest], Optional[bytes]]:
        try:
            if len(raw_line) > 256:
                return None, make_http_response_bytes(HTTPStatus.BAD_REQUEST, "Request line too long")

            if not raw_line:
                return None, make_http_response_bytes(HTTPStatus.BAD_REQUEST, "Empty request")

            requestline = raw_line.decode('iso-8859-1').rstrip('\r\n')
            words = requestline.split()

            if len(words) != 3:
                return None, make_http_response_bytes(HTTPStatus.BAD_REQUEST, "Bad request syntax")

            command, path, version = words

            if command != 'GET':
                return None, make_http_response_bytes(HTTPStatus.METHOD_NOT_ALLOWED, f"Method {command} not allowed")

            if not version.startswith('HTTP/'):
                return None, make_http_response_bytes(HTTPStatus.BAD_REQUEST, "Invalid protocol version")

            if path.startswith('//'):
                path = '/' + path.lstrip('/')

            return ParsedRequest(
                method=command,
                path=path,
                version=version,
                client_ip=client_ip
            ), None

        except Exception as e:
            return None, make_http_response_bytes(HTTPStatus.BAD_REQUEST, f"Parsing error: {str(e)}")

    @classmethod
    async def _handle_client_asyncio(
        cls,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        *,
        timeout: int|float = 2
    ):
        peer = writer.get_extra_info("peername")
        client_ip = peer[0] if peer else "unknown"

        try:
            raw_line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        except asyncio.TimeoutError:
            error_bytes = make_http_response_bytes(HTTPStatus.BAD_REQUEST, "Read timeout")
            writer.write(error_bytes)
        else:
            request, error_bytes = cls._parse_request(raw_line, client_ip)
        
            if error_bytes:
                writer.write(error_bytes)
            else:
                if request:
                    if request.path == "/healthz":
                        response = make_http_response_bytes(HTTPStatus.OK)
                    elif request.path == "/readyz":
                        urds = cls.manager.get_unreadinesses()
                        if not urds:
                            if not cls.manager.get_readiness_points():
                                urd_reason = {
                                    "reason": "Nothing Registred",
                                }
                                body = dumps(urd_reason).encode("utf-8")
                                headers = (
                                    f"HTTP/1.1 503 Service Unavailable\r\n"
                                    f"Content-Type: application/json; charset=utf-8\r\n"
                                    f"Content-Length: {len(body)}\r\n"
                                    f"Connection: close\r\n\r\n"
                                ).encode('iso-8859-1')
                                response = headers + body
                            else:
                                response = make_http_response_bytes(HTTPStatus.OK)
                        else:
                            urd_reason = {
                                "reason": "Unreadinesses",
                                "details": urds
                            }
                            body = dumps(urd_reason).encode("utf-8")
                            headers = (
                                f"HTTP/1.1 503 Service Unavailable\r\n"
                                f"Content-Type: application/json; charset=utf-8\r\n"
                                f"Content-Length: {len(body)}\r\n"
                                f"Connection: close\r\n\r\n"
                            ).encode('iso-8859-1')
                            response = headers + body
                    else:
                        response = make_http_response_bytes(HTTPStatus.NOT_FOUND)
                else:
                    response = make_http_response_bytes(HTTPStatus.NOT_FOUND)
                    
                writer.write(response)
        finally:
            try:
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except OSError:
                    pass

    @classmethod
    async def start_server(cls, host: str, port: int|str, timeout: int|float) -> Optional[asyncio.Task]:
        if cls.is_server_active:
            log.info("Tried to start the HealthCheck server when it was active")
            return
        if not isinstance(host, str):
            message = f"Host argument must be string (not {type(host)}) type"
            log.error(message)
            raise TypeError(message)
        if not isinstance(port, (int, str)):
            message = f"Port argument must be string or integer (not {type(port)}) type"
            log.error(message)
            raise TypeError(message)

        server = await asyncio.start_server(
            partial(cls._handle_client_asyncio, timeout=timeout),
            host=host, port=port
        )
        server_task = asyncio.create_task(server.serve_forever())
        cls.is_server_active = True
        log.info(f"HealthCheck server running on http://{host}:{port}")
        return server_task


start_healthchecks = _HealthCheck.start_server
readiness_point = _HealthCheck.manager.readiness_point
del_readiness_point = _HealthCheck.manager.delete_readiness_point
set_unready = _HealthCheck.manager.set_unready
set_ready = _HealthCheck.manager.set_ready


__all__ = [
    "start_healthchecks",
    "readiness_point",
    "del_readiness_point",
    "set_unready",
    "set_ready"
]
