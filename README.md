# Semantic registry of data models

A local-first FastAPI and React application that indexes OCI repositories from a registry such as Harbor and exposes a cached catalogue of semantic data models.

## Shape of the registry

- One OCI repository represents one data model.
- Tags represent versions.
- OCI manifest/config annotations provide the first searchable metadata.
- Layers represent serialisations such as OWL, SHACL, UML or HTML documentation.

## Local run

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `OCI_REGISTRY_URL`, `OCI_USERNAME`, `OCI_PASSWORD` and `ADMIN_TOKEN`.
3. Start the app:

```bash
docker compose up --build
```

The frontend runs at `http://localhost:5173` and the API at `http://localhost:8000`.

Harbor robot usernames can contain `$`. Keep them as-is in `backend/.env`, for example `OCI_USERNAME=robot$semantic-registry`; the file is mounted into the backend container and read by the Python app directly.

## Allowlist

`OCI_ALLOWLIST` is comma-separated and uses gitignore-like glob patterns. The default `*` includes every repository discoverable through the standard OCI catalog endpoint.

```dotenv
OCI_ALLOWLIST=semantic-models/**,!semantic-models/experimental/**
```

Patterns are evaluated in order, so later excludes can override earlier includes.

## Metadata annotations

The v1 summary fields use this priority:

- `org.opencontainers.image.title`, falling back to repository name
- `org.opencontainers.image.description`
- `org.opencontainers.image.created`, falling back to empty date
- `org.opencontainers.image.version`
- `org.opencontainers.image.licenses`
- `eu.europa.publications.datamodel.domain`, preferably a JSON array but CSV is also accepted
- `eu.europa.publications.datamodel.adms`, stored as raw JSON/JSON-LD when parseable

## API

- `GET /api/datamodels`
- `GET /api/datamodels/{id}`
- `GET /api/datamodels/{id}/layers/{digest}/download`
- `POST /api/admin/sync` with header `X-Admin-Token`

The frontend only queries the local backend database. Registry calls happen during scheduled or manual sync.
