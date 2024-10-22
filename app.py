from typing import List, Union
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from json import dumps

from requests import post
from fastapi import FastAPI, Response, Header, status
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from contextlib import asynccontextmanager

def fastapi_serve(dir: str, ref: str, indexes: List[str] = ["index.html", "index.htm"]) -> Response:
    url_path = urlparse(ref or "/").path
    root = Path(dir)

    try_files = []

    if url_path.endswith("/"):
        try_files += [root / url_path.lstrip("/") / i for i in indexes]

    try_files += [root / url_path]

    try_files_tried = [t for t in try_files if t.is_file()]

    print(try_files, try_files_tried)

    if not try_files_tried:
        return PlainTextResponse("指定されたファイルが見つかりません", status.HTTP_404_NOT_FOUND)

    path = try_files_tried[0]

    print(path, "をサーブ中")

    return FileResponse(path)

ctx = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx["daily"] = Path("analytics_daily.txt").read_text("UTF-8")
    ctx["hourly"] = Path("analytics_hourly.txt").read_text("UTF-8")
    print(ctx)
    yield
    ctx.clear()

app = FastAPI(lifespan=lifespan)

@app.get("/api/cloudflare")
async def cloudflare(zone_id: str, x_token: Union[str, None] = Header()):
    now = datetime.now()
    before = now - timedelta(**{ "days": 30 })

    variables = {
        "zoneTag": zone_id,
        "from": before.astimezone(timezone.utc).strftime("%Y-%m-%d"),
        "to": now.astimezone(timezone.utc).strftime("%Y-%m-%d"),
        "limit": 30
    }

    result = post(
        url="https://api.cloudflare.com/client/v4/graphql",
        headers={
            "Authorization": f"Bearer {x_token}"
        },
        data=dumps({
            "query": ctx["daily"],
            "variables": variables
        })
    )

    json = result.json()
    res = JSONResponse(json)
    if "data" in json and not json["errors"]:
        res.headers["Cache-Control"] = f"public, max-age=60, s-maxage=60"
        res.headers["CDN-Cache-Control"] = f"max-age=60"
    else:
        res.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        res.headers["Cache-Control"] = f"public, max-age=0, s-maxage=0"
        res.headers["CDN-Cache-Control"] = f"max-age=0"
    return res

@app.get("/api/cloudflare2")
async def cloudflare2(zone_id: str, x_token: Union[str, None] = Header()):
    now = datetime.now()
    before = now - timedelta(**{ "hours": 72 })

    variables = {
        "zoneTag": zone_id,
        "from": before.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": 72
    }

    result = post(
        url="https://api.cloudflare.com/client/v4/graphql",
        headers={
            "Authorization": f"Bearer {x_token}"
        },
        data=dumps({
            "query": ctx["hourly"],
            "variables": variables
        })
    )

    json = result.json()
    res = JSONResponse(json)
    if "data" in json and not json["errors"]:
        res.headers["Cache-Control"] = f"public, max-age=60, s-maxage=60"
        res.headers["CDN-Cache-Control"] = f"max-age=60"
    else:
        res.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        res.headers["Cache-Control"] = f"public, max-age=0, s-maxage=0"
        res.headers["CDN-Cache-Control"] = f"max-age=0"
    return res

@app.get("/")
@app.get("/{ref:path}")
async def home(ref: str = None):
    res = fastapi_serve("static", ref)
    res.headers["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    res.headers["CDN-Cache-Control"] = "max-age=3600"
    return res
