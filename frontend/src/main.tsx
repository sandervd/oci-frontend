import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import DOMPurify from "dompurify";
import { Calendar, Database, Download, Filter, Search, X } from "lucide-react";
import "./styles.css";

type FacetValue = { value: string; count: number };
type DataModelSummary = {
  id: number;
  repository: string;
  title: string;
  description: string;
  license: string | null;
  domains: string[];
  latest_tag: string | null;
  updated_at: string | null;
};
type Layer = { digest: string; media_type: string; size: number | null; annotations: Record<string, unknown> };
type Version = {
  tag: string;
  version: string | null;
  digest: string | null;
  title: string;
  description: string;
  license: string | null;
  domains: string[];
  release_date: string | null;
  media_type: string | null;
  annotations: Record<string, unknown>;
  adms: unknown;
  layers: Layer[];
};
type DataModelDetail = DataModelSummary & { latest_digest: string | null; versions: Version[] };
type SearchResponse = {
  items: DataModelSummary[];
  total: number;
  projects: FacetValue[];
  licenses: FacetValue[];
  domains: FacetValue[];
};

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";
const pageSize = 48;

function App() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<SearchResponse | null>(null);
  const [selected, setSelected] = useState<DataModelDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const loadingMoreRef = useRef(false);
  const selectedId = params.get("model");
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasMore = items.length < total;

  const searchKey = useMemo(() => {
    const query = new URLSearchParams(params);
    query.delete("model");
    query.delete("limit");
    query.delete("offset");
    query.sort();
    return query.toString();
  }, [params]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const query = new URLSearchParams(searchKey);
    query.set("limit", String(pageSize));
    query.set("offset", "0");
    fetch(`${apiBase}/api/datamodels?${query.toString()}`, { signal: controller.signal })
      .then((response) => response.json())
      .then(setData)
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [searchKey]);

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || !hasMore || loading || loadingMore) {
      return;
    }

    const controller = new AbortController();
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || loadingMoreRef.current) {
          return;
        }
        loadingMoreRef.current = true;
        setLoadingMore(true);
        const query = new URLSearchParams(searchKey);
        query.set("limit", String(pageSize));
        query.set("offset", String(items.length));
        fetch(`${apiBase}/api/datamodels?${query.toString()}`, { signal: controller.signal })
          .then((response) => response.json())
          .then((nextPage: SearchResponse) => {
            setData((current) => {
              if (!current) {
                return nextPage;
              }
              const knownIds = new Set(current.items.map((item) => item.id));
              const nextItems = nextPage.items.filter((item) => !knownIds.has(item.id));
              return {
                ...nextPage,
                items: [...current.items, ...nextItems],
              };
            });
          })
          .finally(() => {
            loadingMoreRef.current = false;
            setLoadingMore(false);
          });
      },
      { rootMargin: "720px 0px" },
    );

    observer.observe(target);
    return () => {
      controller.abort();
      observer.disconnect();
    };
  }, [hasMore, items.length, loading, searchKey]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    const controller = new AbortController();
    fetch(`${apiBase}/api/datamodels/${selectedId}`, { signal: controller.signal })
      .then((response) => response.json())
      .then(setSelected);
    return () => controller.abort();
  }, [selectedId]);

  const activeFilters = useMemo(() => {
    return ["q", "project", "license", "domain", "released_from", "released_to"].filter((key) => params.has(key)).length;
  }, [params]);

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <span className="flag" aria-hidden="true" />
          <div>
            <h1>Semantic registry of data models</h1>
            <p>OCI-hosted models, versions, serialisations and metadata</p>
          </div>
        </div>
        <div className="status">
          <Database size={18} />
          {data ? `${data.total} data models` : "Loading"}
        </div>
      </header>

      <section className="workspace">
        <aside className="filters">
          <div className="filter-title">
            <Filter size={18} />
            <span>Filters</span>
            {activeFilters > 0 && (
              <button className="icon-button" title="Clear filters" onClick={() => setParams(new URLSearchParams())}>
                <X size={16} />
              </button>
            )}
          </div>
          <label className="searchbox">
            <Search size={18} />
            <input
              value={params.get("q") ?? ""}
              placeholder="Search title or description"
              onChange={(event) => updateParam(params, setParams, "q", event.target.value)}
            />
          </label>
          <Facet title="Project" name="project" values={data?.projects ?? []} params={params} setParams={setParams} />
          <Facet title="License" name="license" values={data?.licenses ?? []} params={params} setParams={setParams} />
          <Facet title="Domain" name="domain" values={data?.domains ?? []} params={params} setParams={setParams} />
          <div className="date-grid">
            <label>
              From
              <input
                type="date"
                value={params.get("released_from") ?? ""}
                onChange={(event) => updateParam(params, setParams, "released_from", event.target.value)}
              />
            </label>
            <label>
              To
              <input
                type="date"
                value={params.get("released_to") ?? ""}
                onChange={(event) => updateParam(params, setParams, "released_to", event.target.value)}
              />
            </label>
          </div>
        </aside>

        <section className="results" aria-busy={loading}>
          <div className="result-head">
            <h2>Data models</h2>
            <span>{loading ? "Refreshing" : `Showing ${items.length} of ${total}`}</span>
          </div>
          <div className="grid">
            {items.map((item) => (
              <button
                className="model-card"
                key={item.id}
                onClick={() => updateParam(params, setParams, "model", String(item.id))}
              >
                <span className="repository">{item.repository}</span>
                <h3>{item.title}</h3>
                <p className="card-description">{plainTextDescription(item.description) || "No description available."}</p>
                <div className="chips">
                  {item.domains.map((domain) => (
                    <span key={domain}>{domain}</span>
                  ))}
                  {item.license && <span>{item.license}</span>}
                </div>
                <div className="meta">
                  <span>{item.latest_tag ?? "untagged"}</span>
                  <span>
                    <Calendar size={14} />
                    {formatDate(item.updated_at)}
                  </span>
                </div>
              </button>
            ))}
          </div>
          <div className="load-more" ref={loadMoreRef}>
            {loadingMore && <span>Loading more data models</span>}
            {!loading && !hasMore && total > 0 && <span>All data models loaded</span>}
          </div>
        </section>
      </section>

      {selected && <DetailPanel model={selected} onClose={() => updateParam(params, setParams, "model", "")} />}
    </main>
  );
}

function Facet({ title, name, values, params, setParams }: FacetProps) {
  return (
    <fieldset>
      <legend>{title}</legend>
      {values.length === 0 && <p className="empty">No values yet</p>}
      {values.map((item) => {
        const checked = params.getAll(name).includes(item.value);
        return (
          <label className="check" key={item.value}>
            <input
              type="checkbox"
              checked={checked}
              onChange={() => toggleParam(params, setParams, name, item.value)}
            />
            <span>{item.value}</span>
            <em>{item.count}</em>
          </label>
        );
      })}
    </fieldset>
  );
}

type FacetProps = {
  title: string;
  name: string;
  values: FacetValue[];
  params: URLSearchParams;
  setParams: (params: URLSearchParams) => void;
};

function DetailPanel({ model, onClose }: { model: DataModelDetail; onClose: () => void }) {
  const safeDescription = sanitizeDescriptionHtml(model.description);

  return (
    <aside className="detail">
      <div className="detail-head">
        <div>
          <span>{model.repository}</span>
          <h2>{model.title}</h2>
        </div>
        <button className="icon-button" title="Close" onClick={onClose}>
          <X size={18} />
        </button>
      </div>
      {safeDescription ? (
        <div className="detail-description" dangerouslySetInnerHTML={{ __html: safeDescription }} />
      ) : (
        <p className="detail-description empty-description">No description available.</p>
      )}
      <div className="version-list">
        {model.versions.map((version) => (
          <details key={version.tag} open={version.tag === model.latest_tag}>
            <summary>
              <strong>{version.tag}</strong>
              <span>{formatDate(version.release_date)}</span>
            </summary>
            <dl>
              <dt>Digest</dt>
              <dd>{version.digest ?? "Unknown"}</dd>
              <dt>License</dt>
              <dd>{version.license ?? "Not specified"}</dd>
              <dt>Domains</dt>
              <dd>{version.domains.join(", ") || "Not specified"}</dd>
            </dl>
            <h3>Serialisations</h3>
            <div className="layers">
              {version.layers.map((layer) => (
                <a
                  key={layer.digest}
                  href={`${apiBase}/api/datamodels/${model.id}/layers/${encodeURIComponent(layer.digest)}/download`}
                >
                  <Download size={16} />
                  <span>{layer.media_type}</span>
                  <small>{formatBytes(layer.size)}</small>
                </a>
              ))}
            </div>
            <details className="raw">
              <summary>Raw annotations</summary>
              <pre>{JSON.stringify(version.annotations, null, 2)}</pre>
            </details>
          </details>
        ))}
      </div>
    </aside>
  );
}

function useSearchParams(): [URLSearchParams, (next: URLSearchParams) => void] {
  const [params, setParamsState] = useState(new URLSearchParams(window.location.search));
  const setParams = (next: URLSearchParams) => {
    const query = next.toString();
    window.history.pushState(null, "", query ? `?${query}` : window.location.pathname);
    setParamsState(new URLSearchParams(next));
  };
  useEffect(() => {
    const onPop = () => setParamsState(new URLSearchParams(window.location.search));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  return [params, setParams];
}

function updateParam(params: URLSearchParams, setParams: (params: URLSearchParams) => void, name: string, value: string) {
  const next = new URLSearchParams(params);
  if (value) {
    next.set(name, value);
  } else {
    next.delete(name);
  }
  setParams(next);
}

function toggleParam(params: URLSearchParams, setParams: (params: URLSearchParams) => void, name: string, value: string) {
  const next = new URLSearchParams(params);
  const values = next.getAll(name);
  next.delete(name);
  values
    .filter((item) => item !== value)
    .forEach((item) => next.append(name, item));
  if (!values.includes(value)) {
    next.append(name, value);
  }
  setParams(next);
}

function formatDate(value: string | null) {
  if (!value) return "No date";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function formatBytes(value: number | null) {
  if (!value) return "";
  return new Intl.NumberFormat("en", { notation: "compact", style: "unit", unit: "byte", unitDisplay: "narrow" }).format(value);
}

function plainTextDescription(value: string) {
  if (!value) {
    return "";
  }
  const withoutTags = value.replace(/<[^>]*>/g, " ");
  const textarea = document.createElement("textarea");
  textarea.innerHTML = withoutTags;
  return textarea.value.replace(/\s+/g, " ").trim();
}

function sanitizeDescriptionHtml(value: string) {
  if (!value) {
    return "";
  }
  return DOMPurify.sanitize(value, {
    ALLOWED_TAGS: [
      "a",
      "abbr",
      "b",
      "br",
      "code",
      "em",
      "i",
      "li",
      "ol",
      "p",
      "pre",
      "span",
      "strong",
      "sub",
      "sup",
      "ul",
    ],
    ALLOWED_ATTR: ["href", "title", "lang"],
    ALLOW_DATA_ATTR: false,
  });
}

createRoot(document.getElementById("root")!).render(<App />);
