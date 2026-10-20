import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getHistory } from "../api.js";
import { BarRow } from "../components/Charts.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock, PageHeader, Pill } from "../components/ui.jsx";
import { fmt, formatDate, scoreTone, trustLabel } from "../utils.js";

const LEVELS = ["HIGH TRUST", "MODERATE TRUST", "LOW TRUST"];

export default function HistoryPage() {
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [category, setCategory] = useState("all");
  const [level, setLevel] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    getHistory().then(setData).catch((err) => setError(err.message));
  }, []);

  const categories = useMemo(
    () => (data ? [...new Set(data.items.map((item) => item.category))] : []),
    [data]
  );

  const rows = useMemo(() => {
    if (!data) return [];

    return data.items.filter(
      (item) =>
        (category === "all" || item.category === category) &&
        (level === "all" || item.trust_level === level) &&
        item.question.toLowerCase().includes(search.trim().toLowerCase())
    );
  }, [data, category, level, search]);

  if (error) return <ErrorBlock message={error} />;
  if (!data) return <LoadingBlock label="Loading history…" />;

  const { stats } = data;
  const maxWins = Math.max(1, ...Object.values(stats.model_wins));

  return (
    <>
      <PageHeader
        title="Research history"
        subtitle="Filter, benchmark, and track verification quality over time."
      >
        <Link className="btn btn-soft" to="/?mode=benchmark">
          Run benchmark →
        </Link>
      </PageHeader>

      <div className="stat-grid">
        <div className="card stat">
          <div className="eyebrow">Average trust</div>
          <div className="stat-value">
            {fmt(stats.average_trust)} <small>/ 10</small>
          </div>
        </div>
        <div className="card stat">
          <div className="eyebrow">High trust runs</div>
          <div className="stat-value">
            {stats.high_trust_pct === null ? "–" : `${Math.round(stats.high_trust_pct)}%`}
          </div>
        </div>
        <div className="card stat">
          <div className="eyebrow">Top winning model</div>
          <div className="stat-value">{stats.top_model || "–"}</div>
        </div>
      </div>

      <div className="card section-gap">
        <div className="card-title-row">
          <h3 className="card-title">Past validations</h3>

          <div className="filters">
            <input
              type="search"
              placeholder="Search questions"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="all">All categories</option>
              {categories.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="all">All levels</option>
              {LEVELS.map((item) => (
                <option key={item} value={item}>
                  {trustLabel(item)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {rows.length === 0 ? (
          <EmptyBlock
            title="No validations match"
            message="Try clearing the filters, or run a new validation."
            action={<Link className="btn btn-primary" to="/">Ask a question</Link>}
          />
        ) : (
          <div className="history-table">
            <div className="history-head">
              <span>Date</span>
              <span>Question</span>
              <span>Category</span>
              <span>Winner</span>
              <span>Trust</span>
            </div>

            {rows.map((item) => (
              <button
                type="button"
                key={item.timestamp + item.question}
                className={"history-row" + (item.run_id ? " clickable" : "")}
                onClick={() => item.run_id && navigate(`/report/${item.run_id}`)}
                title={item.run_id ? "Open full report" : "Summary only — no saved report"}
              >
                <span className="muted">{formatDate(item.timestamp)}</span>
                <span className="history-q">{item.question}</span>
                <span className="muted">{item.category}</span>
                <span>{item.winner}</span>
                <span>
                  <Pill tone={scoreTone(item.trust_score)}>
                    {fmt(item.trust_score)} / 10
                  </Pill>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="two-col section-gap">
        <div className="card">
          <h3 className="card-title">Average trust by category</h3>
          {Object.entries(stats.category_average).map(([name, value]) => (
            <BarRow key={name} label={name} value={value} />
          ))}
        </div>

        <div className="card">
          <h3 className="card-title">Winning models</h3>
          {Object.entries(stats.model_wins).map(([name, count]) => (
            <BarRow key={name} label={name} value={count} max={maxWins} tone="navy" digits={0} />
          ))}
        </div>
      </div>
    </>
  );
}
