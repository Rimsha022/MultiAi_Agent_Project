import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useReport } from "../hooks.js";
import { ErrorBlock, LoadingBlock, Notice, PageHeader, Pill, ScoreCard } from "../components/ui.jsx";
import { exportReportPdf } from "../pdf/exportPdf.jsx";
import {
  buildCitation,
  copyText,
  fmt,
  trustLabel,
  trustTone,
} from "../utils.js";

export default function ReportPage() {
  const { id } = useParams();
  const { run, error } = useReport(id);
  const [copied, setCopied] = useState(false);
  const [exporting, setExporting] = useState(false);

  if (error) {
    return (
      <ErrorBlock
        title="Report not found"
        message={error}
        action={<Link className="btn btn-primary" to="/">Back to Ask</Link>}
      />
    );
  }

  if (!run) return <LoadingBlock label="Loading report…" />;

  if (!run.result) {
    return (
      <ErrorBlock
        title="This run has no report"
        message={run.error || "The validation did not finish."}
        action={<Link className="btn btn-primary" to="/">Try again</Link>}
      />
    );
  }

  const { result } = run;
  const tone = trustTone(result.trust_level);
  const { claims_summary: summary } = result;

  async function exportPdf() {
    setExporting(true);

    try {
      await exportReportPdf(run);
    } finally {
      setExporting(false);
    }
  }

  async function copyCitation() {
    const ok = await copyText(buildCitation(run));
    setCopied(ok);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <>
      <PageHeader
        title="Verification report"
        subtitle="A clear verdict first. Evidence and scoring available on demand."
      >
        <span className="run-tag">{run.id}</span>
      </PageHeader>

      <p className="report-question">
        <span className="eyebrow">Question</span>
        {run.question.trim()}
      </p>

      {!result.valid && (
        <Notice
          level="warning"
          title="Incomplete validation"
          message={
            result.validation_errors.join(" | ") +
            " — this run was not saved to the experiment log."
          }
        />
      )}

      <div className="report-grid">
        <div className="card card-navy trust-card">
          <div className="eyebrow light">Trust index</div>
          <div className="trust-value">
            <span className="trust-num">{fmt(result.trust_score)}</span>
            <span className="trust-of">/ 10</span>
          </div>
          <Pill tone={tone}>{trustLabel(result.trust_level)}</Pill>
          <p className="trust-claims">
            {summary.supported} / {summary.total} claims supported
          </p>
        </div>

        <div className="card answer-card">
          <div className="answer-head">
            <span className="eyebrow accent">Verified answer</span>
            {result.corrections.length > 0 && (
              <Pill tone="amber">
                {result.corrections.length} correction
                {result.corrections.length > 1 ? "s" : ""}
              </Pill>
            )}
          </div>

          <p className="answer-text">{result.verified_answer}</p>

          {result.corrections.length > 0 && (
            <ul className="correction-list">
              {result.corrections.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          )}

          <div className="answer-foot">
            Winning model: <strong>{result.winning_model.toUpperCase()}</strong>
            <span>|</span>
            {result.models_compared} models compared
          </div>
        </div>
      </div>

      <div className="score-grid">
        <ScoreCard label="Quality" value={result.scores.quality} />
        <ScoreCard label="Consistency" value={result.scores.consistency} />
        <ScoreCard label="Verification" value={result.scores.verification} />
        <ScoreCard label="Evidence" value={result.scores.evidence} />
      </div>

      <div className="report-actions">
        <div className="text-actions">
          <button
            type="button"
            className="link-button"
            onClick={exportPdf}
            disabled={exporting}
          >
            {exporting ? "Preparing PDF…" : "Export PDF"}
          </button>
          <button type="button" className="link-button" onClick={copyCitation}>
            {copied ? "Copied ✓" : "Copy citation"}
          </button>
        </div>

        <Link className="btn btn-primary" to={`/report/${run.id}/answers`}>
          Explore details →
        </Link>
      </div>
    </>
  );
}
