# hcheckz

Tiny asynchronous healthcheck server.

## Installation

```bash
pip install hcheckz
```

## Usage

```python
import asyncio
import hcheckz

async def main():
    # Start the healthcheck server in the background
    hcheck_task = hcheckz.start_healthchecks(host="0.0.0.0", port=8080)
    
    # Register your dependency points
    hcheckz.readiness_point("kafka")
    hcheckz.readiness_point("redis")
    
    # Start main application background tasks
    await asyncio.sleep(2) 
    hcheckz.set_ready("kafka")

    await asyncio.sleep(2) 
    hcheckz.set_ready("redis")

    
    # Keep the main loop alive and handle graceful shutdown
    try:
        await asyncio.Event().wait() 
    except asyncio.CancelledError:
        hcheck_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
```

## Endpoints:

- /healthz
- /readyz

### /healthz
`200 OK` status if service is at least running

### /readyz
`200 OK` status if all of readiness points are ready and registred more than zero readiness points unless `503 Service Unavailable`

__200 OK__

> [!example]- text/plain
>```text
> 200 OK
> ```

__503 Service Unavailable__ (0 points registred)
> [!example]- applixation/json
>```json
> {
>     "reason": "Nothing Registred"
> }
> ```

__503 Service Unavailable__ (problems)
> [!example]- applixation/json
>```json
> {
>     "reason": "Unreadinesses",
>     "details": {
>         "kafka": {
>             "code": "FATAL ERROR",
>             "message": "Some unknown fatal error, Kafka dead."
>         }
>     }
> }
> ```

## HTTP Status Codes Reference

- 200 OK
- 400 Bad Request
- 404 Not Found
- 405 Method Not Allowed
- 503 Service Unavailable

### 200 OK
Always returns `text/plain` body: `200 OK`

### 400 Bad Request
Always returns `text/plain` body
> [!example]- text/plain
>```text
> 400 Bad Request: Request line too long
> ```

### 404 Not Found
Always returns `text/plain` body
> [!example]- text/plain
>```text
> 404 Not Found
> ```

### 405 Method Not Allowed
Always returns `text/plain` body
> [!example]- text/plain
>```text
> 405 Method Not Allowed
> ```

### 503 Service Unavailable
Always returns `application/json` body
Watch endpoint [[README.md#readyz/|readyz/]]
