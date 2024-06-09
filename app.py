from typing import List, Union
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from json import dumps

from requests import post
from fastapi import FastAPI, Response, Header, status
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse

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

app = FastAPI()

@app.get("/cloudflare")
async def cloudflare(zone_id: str, x_token: Union[str, None] = Header()):
    query = Path("analytics_daily.txt").read_text("UTF-8")

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
            "query": query,
            "variables": variables
        })
    )

    res = JSONResponse(result.json(), result.status_code)
    res.headers["Cache-Control"] = f"public, max-age=60, s-maxage=60"
    res.headers["CDN-Cache-Control"] = f"max-age=60"
    return res

@app.get("/")
@app.get("/{ref:path}")
async def home(ref: str = None):
    res = fastapi_serve("static", ref)
    res.headers["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    res.headers["CDN-Cache-Control"] = "max-age=3600"
    return res
