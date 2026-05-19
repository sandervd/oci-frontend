import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
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
type SearchResponse = { items: DataModelSummary[]; total: number; licenses: FacetValue[]; domains: FacetValue[] };

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

function App() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<SearchResponse | null>(null);
  const [selected, setSelected] = useState<DataModelDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const selectedId = params.get("model");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const query = new URLSearchParams(params);
    query.delete("model");
    fetch(`${apiBase}/api/datamodels?${query.toString()}`, { signal: controller.signal })
      .then((response) => response.json())
      .then(setData)
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [params]);

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
    return ["q", "license", "domain", "released_from", "released_to"].filter((key) => params.has(key)).length;
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
            {loading && <span>Refreshing</span>}
          </div>
          <div className="grid">
            {(data?.items ?? []).map((item) => (
              <button
                className="model-card"
                key={item.id}
                onClick={() => updateParam(params, setParams, "model", String(item.id))}
              >
                <span className="repository">{item.repository}</span>
                <h3>{item.title}</h3>
                <p>{item.description || "No description available."}</p>
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
      <p>{model.description}</p>
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

createRoot(document.getElementById("root")!).render(<App />);
