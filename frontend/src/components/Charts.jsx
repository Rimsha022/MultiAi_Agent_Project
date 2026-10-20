import { fmt } from "../utils.js";

export function BarRow({ label, value, max = 10, tone = "indigo", digits = 1 }) {
  const width = Math.max(0, Math.min(100, (value / max) * 100));

  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <div className="bar-track">
        <div className={`bar-fill fill-${tone}`} style={{ width: `${width}%` }} />
      </div>
      <span className="bar-value">{fmt(value, digits)}</span>
    </div>
  );
}

// Similarity matrix; cell shade grows with agreement.
export function Heatmap({ models, matrix }) {
  return (
    <div
      className="heatmap"
      style={{ gridTemplateColumns: `90px repeat(${models.length}, 1fr)` }}
    >
      <span />
      {models.map((model) => (
        <span key={model} className="heat-head">
          {model}
        </span>
      ))}

      {models.map((rowModel, row) => (
        <HeatRow
          key={rowModel}
          label={rowModel}
          values={matrix[row]}
          row={row}
        />
      ))}
    </div>
  );
}

function HeatRow({ label, values, row }) {
  return (
    <>
      <span className="heat-label">{label}</span>
      {values.map((value, col) => {
        const pct = Math.round(value * 100);
        const alpha = 0.12 + Math.max(0, Math.min(1, value)) * 0.38;

        return (
          <span
            key={col}
            className={"heat-cell" + (row === col ? " heat-self" : "")}
            style={{ background: `rgba(91, 110, 240, ${alpha})` }}
          >
            {pct}%
          </span>
        );
      })}
    </>
  );
}

// Stacked bar showing how much each component adds to the final score.
export function ContributionBar({ weights, scores }) {
  const parts = [
    { key: "quality", label: "Quality", tone: "indigo" },
    { key: "verification", label: "Verification", tone: "navy" },
    { key: "evidence", label: "Evidence", tone: "green" },
    { key: "consistency", label: "Consistency", tone: "amber" },
  ].filter(
    (part) => weights[part.key] !== undefined && scores[part.key] !== null
  );

  const contributions = parts.map((part) => ({
    ...part,
    weight: weights[part.key],
    points: weights[part.key] * scores[part.key],
  }));

  const total = contributions.reduce((sum, part) => sum + part.points, 0) || 1;

  return (
    <div>
      <div className="stack-bar">
        {contributions.map((part) => (
          <div
            key={part.key}
            className={`fill-${part.tone}`}
            style={{ width: `${(part.points / total) * 100}%` }}
            title={`${part.label}: ${fmt(part.points, 2)} points`}
          />
        ))}
      </div>

      <ul className="legend">
        {contributions.map((part) => (
          <li key={part.key}>
            <span className={`dot fill-${part.tone}`} />
            {part.label} {Math.round(part.weight * 100)}%
            <em>+{fmt(part.points, 2)}</em>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Donut of supported / contradicted / insufficient claims.
export function ClaimDonut({ summary }) {
  const segments = [
    { key: "supported", color: "var(--green)", value: summary.supported },
    { key: "contradicted", color: "var(--red)", value: summary.contradicted },
    { key: "insufficient", color: "var(--amber)", value: summary.insufficient },
    { key: "errors", color: "var(--muted)", value: summary.errors || 0 },
  ];

  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;

  return (
    <div className="donut">
      <svg viewBox="0 0 120 120" width="140" height="140" role="img">
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="var(--line)"
          strokeWidth="14"
        />
        {total > 0 &&
          segments
            .filter((segment) => segment.value > 0)
            .map((segment) => {
              const length = (segment.value / total) * circumference;
              const circle = (
                <circle
                  key={segment.key}
                  cx="60"
                  cy="60"
                  r={radius}
                  fill="none"
                  stroke={segment.color}
                  strokeWidth="14"
                  strokeDasharray={`${length} ${circumference - length}`}
                  strokeDashoffset={-offset}
                  transform="rotate(-90 60 60)"
                />
              );
              offset += length;
              return circle;
            })}
        <text x="60" y="58" textAnchor="middle" className="donut-num">
          {summary.supported}
        </text>
        <text x="60" y="76" textAnchor="middle" className="donut-cap">
          supported
        </text>
      </svg>

      <ul className="legend">
        <li>
          <span className="dot" style={{ background: "var(--green)" }} />
          {summary.supported} supported
        </li>
        <li>
          <span className="dot" style={{ background: "var(--red)" }} />
          {summary.contradicted} contradicted
        </li>
        <li>
          <span className="dot" style={{ background: "var(--amber)" }} />
          {summary.insufficient} insufficient
        </li>
        {summary.errors > 0 && (
          <li>
            <span className="dot" style={{ background: "var(--muted)" }} />
            {summary.errors} errors
          </li>
        )}
      </ul>
    </div>
  );
}
