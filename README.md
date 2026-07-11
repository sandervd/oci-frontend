# Semantic Registry of Data Models

A local-first FastAPI and React application that indexes OCI repositories from registries such as Harbor and exposes a cached catalogue of semantic data models.

The Semantic Registry represents a joint innovation effort between the **SEMIC initiative** and the **Reference Data Management team of the Publications Office of the European Union**. It explores a new publication architecture for semantic interoperability assets, based on cloud-native technologies and open standards, while preserving the governance, quality assurance and discoverability principles that have made **EU Vocabularies** the authoritative semantic infrastructure for European institutions.

The project demonstrates how semantic resources can be managed, versioned, distributed and consumed using **OCI (Open Container Initiative) registries**, introducing a modern publication model inspired by software engineering best practices. Rather than considering ontologies, application profiles or controlled vocabularies as static downloadable files, the registry treats them as versioned software artefacts that can participate in automated publication workflows, CI/CD pipelines and federated semantic ecosystems.

---

# Strategic Vision

The Publications Office has established one of the world's largest semantic infrastructures through **EU Vocabularies**, providing authoritative multilingual reference data, controlled vocabularies, authority tables, ontologies and application profiles used by the European institutions, Member States and numerous European interoperability initiatives.

As semantic technologies continue to evolve, new types of semantic assets are emerging:

- conceptual and logical data models
- canonical information models
- ontology networks
- SHACL validation rules
- application profiles
- UML models
- JSON schemas
- XML schemas
- documentation
- implementation artefacts
- software packages associated with semantic models

These assets increasingly evolve like software rather than static publications. They require continuous versioning, automated validation, dependency management, reproducible releases and machine-oriented distribution.

The Semantic Registry investigates how OCI registries can complement the existing publication infrastructure by providing these capabilities while remaining fully compatible with the governance model of EU Vocabularies.

The objective is **not to replace the existing publication platform**, but to extend it with an additional publication mechanism that supports modern semantic engineering practices.

---

# Towards a Federated Vocabulary Hub

The longer-term vision is the evolution of the **EU Vocabularies website** from a central publication portal into a **federated European Semantic Hub**.

Instead of requiring every semantic resource to be physically hosted within a single infrastructure, organisations would be able to publish semantic assets in trusted OCI registries under their own governance while making them discoverable through a common European catalogue.

This enables:

- distributed publication
- decentralised ownership
- common discovery
- central metadata indexing
- authoritative governance
- interoperability across repositories

The Publications Office remains responsible for governance, quality and discoverability, while publishers maintain ownership of their semantic artefacts.

The Semantic Registry therefore acts as a federation layer capable of harvesting metadata from multiple OCI registries and exposing a unified catalogue to users and applications.

---

# Supporting the European Interoperability Ecosystem

The registry is designed to become a building block for the wider European interoperability landscape.

It supports publication and discovery of semantic assets used by:

- SEMIC
- EU Vocabularies
- Interoperable Europe
- Data Spaces
- European institutions
- Member States
- EU-funded projects
- public administrations

By relying entirely on open standards (OCI, HTTP, JSON, RDF, OWL, SHACL, ADMS and DCAT), the registry enables semantic resources to remain interoperable regardless of where they are physically hosted.

The registry therefore supports both institutional publication workflows and community-driven publication models.

---

# Benefits

The Semantic Registry introduces several capabilities that are difficult to achieve through traditional document-oriented publication approaches.

## Cloud-native publication

Semantic resources become OCI artefacts that can be published using standard container registries.

## Native version management

Every version of a semantic resource is immutable and uniquely identifiable.

## Automated publication

Semantic artefacts can be automatically published through CI/CD pipelines directly from Git repositories.

## Reproducibility

Published artefacts remain reproducible over time, supporting governance and traceability.

## Federation

Multiple trusted registries can participate in a common discovery infrastructure without centralising their content.

## Metadata-driven discovery

OCI manifest annotations provide rich searchable metadata that can later be complemented with semantic metadata extracted from the artefacts themselves.

## Extensibility

New semantic artefact types can be introduced without modifying the publication architecture.

---

# Relationship with EU Vocabularies

The Semantic Registry is conceived as a complementary publication channel for the EU Vocabularies ecosystem.

While EU Vocabularies continues to provide authoritative publication, governance, multilingual management and persistent identifiers, the registry explores how semantic resources can additionally be:

- published directly from engineering workflows
- versioned through OCI registries
- harvested automatically
- synchronised across organisations
- indexed into a federated catalogue

Future interoperability may include:

- synchronisation with EU Vocabularies metadata
- harvesting of OCI registries
- publication of application profiles
- publication of ontology releases
- publication of SHACL validation packages
- publication of semantic data models
- publication of implementation artefacts

This creates an alternative route for publishing semantic resources while preserving the quality assurance processes already established by the Publications Office.

---

# Architecture

## Shape of the registry

- One OCI repository represents one semantic data model.
- Tags represent published versions.
- OCI manifest and config annotations provide the primary searchable metadata.
- Layers contain different serialisations such as:
  - OWL
  - RDF
  - SHACL
  - UML
  - HTML documentation
  - JSON Schema
  - XML Schema
  - additional implementation artefacts

The frontend queries only the local catalogue.

The backend periodically synchronises with remote OCI registries, harvesting repository metadata, versions and available artefacts.

Future evolutions may include semantic enrichment, automatic metadata extraction, validation workflows and integration with the wider EU semantic infrastructure.

---

# Metadata annotations

The registry currently indexes OCI annotations such as:

- `org.opencontainers.image.title`
- `org.opencontainers.image.description`
- `org.opencontainers.image.created`
- `org.opencontainers.image.version`
- `org.opencontainers.image.licenses`
- `eu.europa.publications.datamodel.domain`
- `eu.europa.publications.datamodel.adms`

The metadata model has intentionally been designed to align with existing European semantic metadata standards, facilitating future interoperability with ADMS, DCAT and the metadata models already used by EU Vocabularies.

---

# Long-term roadmap

The Semantic Registry represents an important step towards a new generation of semantic publication infrastructures.

Future developments may include:

- federation across multiple OCI registries
- semantic metadata harvesting
- automatic validation pipelines
- integration with VocBench publication workflows
- synchronisation with EU Vocabularies
- persistent identifiers
- semantic search
- dependency visualisation
- provenance tracking
- digital signatures
- trust and governance mechanisms
- API-based publication
- machine-readable release management
- AI-assisted discovery of semantic assets

The long-term ambition is to provide the European interoperability community with a modern semantic publication infrastructure that combines the governance and authority of EU Vocabularies with the flexibility, automation and scalability of cloud-native technologies.
