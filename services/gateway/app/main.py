from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from hotstar_common.app import create_service_app

from .config import get_settings
from .proxy import close_client, get_client, router, upstream_status

settings = get_settings()

app = create_service_app(
    name="api-gateway",
    title="hotstar API Gateway",
    description="Single entry point for the hotstar platform. Routes /api/<service>/... to the internal microservices, "
    "authenticates requests at the edge and streams uploads/video with Range support. Use the service selector (top right) "
    "to browse each service's API, then click Authorize and paste an access token.",
    routers=[router],
    on_shutdown=close_client,
    default_readiness=False,  # gateway defines its own /ready: ready only when every upstream answers
    swagger_ui_parameters={
        "urls": [{"name": n, "url": f"/api/openapi/{n}.json"} for n in settings.upstreams],
        "urls.primaryName": "auth",
        "persistAuthorization": True,
    },
    log_level=settings.log_level,
)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()], allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID", "Content-Range", "Accept-Ranges"], allow_credentials=False)


@app.get("/ready", include_in_schema=False)
async def ready(client=Depends(get_client)):
    status = await upstream_status(client)
    ok = all(v == "ok" for v in status.values())
    return JSONResponse({"status": "ready" if ok else "not_ready", "service": "api-gateway", "checks": status}, status_code=200 if ok else 503)
