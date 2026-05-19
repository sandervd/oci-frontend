from collections.abc import AsyncIterator
from http import HTTPStatus
from urllib.parse import quote

import httpx


class OCIClient:
    def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password) if username and password else None

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=30.0, follow_redirects=True) as client:
            response = await client.request(method, path, **kwargs)
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                token = await self._bearer_token(client, response.headers.get("WWW-Authenticate"))
                if token:
                    headers = dict(kwargs.pop("headers", {}) or {})
                    headers["Authorization"] = f"Bearer {token}"
                    response = await client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response

    async def _bearer_token(self, client: httpx.AsyncClient, challenge: str | None) -> str | None:
        if not challenge or not challenge.lower().startswith("bearer "):
            return None
        params = _parse_auth_params(challenge[7:])
        realm = params.pop("realm", None)
        if not realm:
            return None
        response = await client.get(realm, params=params, auth=self.auth)
        response.raise_for_status()
        payload = response.json()
        return payload.get("token") or payload.get("access_token")

    async def catalog(self) -> list[str]:
        repositories: list[str] = []
        path = "/v2/_catalog?n=1000"
        while path:
            response = await self._request("GET", path)
            repositories.extend(response.json().get("repositories", []))
            path = _next_link(response.headers.get("Link"))
        return repositories

    async def tags(self, repository: str) -> list[str]:
        path = f"/v2/{repository}/tags/list?n=1000"
        tags: list[str] = []
        while path:
            response = await self._request("GET", path)
            tags.extend(response.json().get("tags") or [])
            path = _next_link(response.headers.get("Link"))
        return tags

    async def manifest(self, repository: str, reference: str) -> tuple[dict, str | None]:
        response = await self._request(
            "GET",
            f"/v2/{repository}/manifests/{quote(reference, safe='')}",
            headers={
                "Accept": ", ".join(
                    [
                        "application/vnd.oci.image.manifest.v1+json",
                        "application/vnd.docker.distribution.manifest.v2+json",
                        "application/vnd.oci.artifact.manifest.v1+json",
                    ]
                )
            },
        )
        return response.json(), response.headers.get("Docker-Content-Digest")

    async def blob_json(self, repository: str, digest: str) -> dict | None:
        response = await self._request("GET", f"/v2/{repository}/blobs/{quote(digest, safe='')}")
        content_type = response.headers.get("Content-Type", "")
        if "json" not in content_type and not response.content.strip().startswith(b"{"):
            return None
        return response.json()

    async def stream_blob(self, repository: str, digest: str) -> tuple[str, AsyncIterator[bytes]]:
        async def iterator() -> AsyncIterator[bytes]:
            async with httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=None, follow_redirects=True) as client:
                path = f"/v2/{repository}/blobs/{quote(digest, safe='')}"
                response = await client.head(path)
                headers = {}
                if response.status_code == HTTPStatus.UNAUTHORIZED:
                    token = await self._bearer_token(client, response.headers.get("WWW-Authenticate"))
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                await response.aclose()
                async with client.stream("GET", path, headers=headers) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk

        manifest_media_type = "application/octet-stream"
        return manifest_media_type, iterator()


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    first = link_header.split(",", 1)[0].strip()
    if not first.startswith("<") or ">" not in first:
        return None
    return first[1 : first.index(">")]


def _parse_auth_params(value: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for part in value.split(","):
        if "=" not in part:
            continue
        key, raw_value = part.split("=", 1)
        params[key.strip()] = raw_value.strip().strip('"')
    return params
