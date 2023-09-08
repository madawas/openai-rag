import httpx
import logging
from fastapi.encoders import jsonable_encoder
from pydantic import HttpUrl

LOG = logging.getLogger(__name__)


async def send_callback(url: HttpUrl, payload):
    client = httpx.AsyncClient()
    req = client.build_request(method="POST", url=url, json=jsonable_encoder(payload))
    response = await client.send(req)
    LOG.debug("Response received for callback- [URL: %s, Response: %s]", url, response)
    await client.aclose()
