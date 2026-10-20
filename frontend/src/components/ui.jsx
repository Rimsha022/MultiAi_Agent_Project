import { fmt, scoreTone } from "../utils.js";

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="subtitle">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function Pill({ tone = "indigo", children }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

export function ScoreCard({ label, value }) {
  return (
    <div className="card score-card">
      <div className="eyebrow">{label}</div>
      <div className="score-card-value">
        <span className={`score-num tone-${scoreTone(value)}`}>
          {fmt(value)}
        </span>
        <span className="score-of">/ 10</span>
      </div>
    </div>
  );
}

export function LoadingBlock({ label = "Loading…" }) {
  return (
    <div className="state-box">
      <div className="spinner" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorBlock({ title = "Something went wrong", message, action }) {
  return (
    <div className="state-box state-error">
      <h3>{title}</h3>
      <p>{message}</p>
      {action}
    </div>
  );
}

export function EmptyBlock({ title, message, action }) {
  return (
    <div className="state-box">
      <h3>{title}</h3>
      <p>{message}</p>
      {action}
    </div>
  );
}

export function Notice({ level = "info", title, message }) {
  return (
    <div className={`notice notice-${level}`}>
      <strong>{title}</strong>
      {message && <span>{message}</span>}
    </div>
  );
}
