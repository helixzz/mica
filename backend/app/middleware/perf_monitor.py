"""In-memory API performance monitor — tracks response times per path."""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_perf_stats: dict[str, list[float]] = defaultdict(list)


class PerfMonitorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed = (time.monotonic() - start) * 1000
        path = request.url.path
        _perf_stats[path].append(elapsed)
        return response


def get_perf_stats() -> dict:
    result = {}
    for path, times in _perf_stats.items():
        result[path] = {
            "count": len(times),
            "avg_ms": round(sum(times) / len(times), 1),
            "max_ms": round(max(times), 1),
        }
    return dict(sorted(result.items(), key=lambda x: x[1]["avg_ms"], reverse=True)[:20])
