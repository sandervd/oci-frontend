from dataclasses import dataclass, field
from urllib.parse import quote

import httpx


@dataclass
class RepositoryDiscovery:
    repository: str
    tag_digests: dict[str, str] = field(default_factory=dict)

    @property
    def tags(self) -> list[str]:
        return sorted(self.tag_digests)


class HarborClient:
    def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password) if username and password else None

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=15.0) as client:
                systeminfo = await client.get("/api/v2.0/systeminfo")
                if systeminfo.status_code >= 400:
                    return False
                projects = await client.get("/api/v2.0/projects", params={"page": 1, "page_size": 1})
                return projects.status_code < 400
        except httpx.RequestError:
            return False

    async def discover_repositories(self) -> list[RepositoryDiscovery]:
        return [RepositoryDiscovery(repository=repository) for repository in await self.list_repositories()]

    async def list_repositories(self) -> list[str]:
        repositories: list[str] = []
        projects = await self._get_paginated("/api/v2.0/projects")
        for project in projects:
            project_name = project.get("name")
            if not project_name:
                continue
            try:
                project_repositories = await self._get_paginated(
                    f"/api/v2.0/projects/{quote(project_name, safe='')}/repositories"
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {403, 404}:
                    continue
                raise
            repositories.extend(repository["name"] for repository in project_repositories if repository.get("name"))
        return sorted(repositories)

    async def discover_repository(self, repository: str) -> RepositoryDiscovery:
        return await self._discover_repository(repository)

    async def discover_repositories_with_artifacts(self) -> list[RepositoryDiscovery]:
        discoveries: list[RepositoryDiscovery] = []
        projects = await self._get_paginated("/api/v2.0/projects")
        for project in projects:
            project_name = project.get("name")
            if not project_name:
                continue
            repositories = await self._get_paginated(f"/api/v2.0/projects/{quote(project_name, safe='')}/repositories")
            for repository in repositories:
                repository_name = repository.get("name")
                if not repository_name:
                    continue
                discovery = await self._discover_repository(repository_name)
                if discovery.tags:
                    discoveries.append(discovery)
        return discoveries

    async def _discover_repository(self, repository: str) -> RepositoryDiscovery:
        project, repository_name = _split_repository(repository)
        artifacts = await self._get_paginated(
            f"/api/v2.0/projects/{quote(project, safe='')}/repositories/{_quote_repository_name(repository_name)}/artifacts",
            params={"with_tag": "true"},
        )
        tag_digests: dict[str, str] = {}
        for artifact in artifacts:
            digest = artifact.get("digest")
            if not digest:
                continue
            for tag in artifact.get("tags") or []:
                tag_name = tag.get("name")
                if tag_name:
                    tag_digests[tag_name] = digest
        return RepositoryDiscovery(repository=repository, tag_digests=tag_digests)

    async def _get_paginated(self, path: str, params: dict | None = None) -> list[dict]:
        items: list[dict] = []
        page = 1
        page_size = 100
        base_params = dict(params or {})
        async with httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=30.0) as client:
            while True:
                response = await client.get(path, params={**base_params, "page": page, "page_size": page_size})
                response.raise_for_status()
                payload = response.json()
                if not payload:
                    break
                items.extend(payload)
                total = int(response.headers.get("X-Total-Count") or 0)
                if total and len(items) >= total:
                    break
                if len(payload) < page_size:
                    break
                page += 1
        return items


def _split_repository(repository: str) -> tuple[str, str]:
    project, separator, repository_name = repository.partition("/")
    if not separator or not repository_name:
        raise ValueError(f"Repository path must include project and repository: {repository}")
    return project, repository_name


def _quote_repository_name(repository_name: str) -> str:
    return quote(repository_name, safe="").replace("%2F", "%252F")
