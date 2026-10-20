import { useState } from "react";
import { Link, NavLink, useParams } from "react-router-dom";

import { useReport } from "../hooks.js";
import {
  BarRow,
  ClaimDonut,
  ContributionBar,
  Heatmap,
} from "../components/Charts.jsx";
import { ErrorBlock, LoadingBlock, PageHeader, Pill } from "../components/ui.jsx";
import { STATUS_META, fmt, scoreTone } from "../utils.js";

const TABS = [
  { key: "answers", label: "Model Answers", title: "Model answers", subtitle: "Compare candidate answers, inspect quality, and expand long responses." },
  { key: "scores", label: "Scores", title: "Scores", subtitle: "Transparent criteria and cross-model agreement." },
  { key: "claims", label: "Claims & Evidence", title: "Claims & evidence", subtitle: "Every claim has a status, confidence, and traceable sources." },
];

const CRITERIA = [
  ["relevance", "Relevance"],
  ["completeness", "Completeness"],
  ["justification", "Justification"],
  ["context_awareness", "Context"],
  ["conciseness", "Conciseness"],
];

export default function DetailsPage() {
  const { id, tab } = useParams();
  const { run, error } = useReport(id);

  const current = TABS.find((item) => item.key === tab) || TABS[0];

  if (error) {
    return (
      <ErrorBlock
        title="Report not found"
        message={error}
        action={<Link className="btn btn-primary" to="/">Back to Ask</Link>}
      />
    );
  }

  if (!run) return <LoadingBlock label="Loading details…" />;
  if (!run.result) {
    return <ErrorBlock title="No details available" message={run.error || ""} />;
  }

  return (
    <>
      <PageHeader
        title={`Result details / ${current.title}`}
        subtitle={current.subtitle}
      >
        <Link className="btn btn-ghost" to={`/report/${id}`}>
          ← Back to report
        </Link>
      </PageHeader>

      <div className="tabs">
        {TABS.map((item) => (
          <NavLink
            key={item.key}
            to={`/report/${id}/${item.key}`}
            className={({ isActive }) => "tab" + (isActive ? " active" : "")}
          >
            {item.label}
          </NavLink>
        ))}
      </div>

      {current.key === "answers" && <AnswersTab result={run.result} />}
      {current.key === "scores" && <ScoresTab result={run.result} />}
      {current.key === "claims" && <ClaimsTab result={run.result} />}
    </>
  );
}

function AnswersTab({ result }) {
  const [open, setOpen] = useState({});

  return (
    <div className="answers-grid">
      {result.answers.map((answer) => {
        const expanded = Boolean(open[answer.model]);

        return (
          <div
            key={answer.model}
            className={"card answer-model" + (answer.selected ? " selected" : "")}
          >
            <div className="answer-model-head">
              <h3>{answer.model}</h3>
              <span className={`score-num tone-${scoreTone(answer.quality)}`}>
                {fmt(answer.quality)}
              </span>
            </div>

            <Pill tone={answer.selected ? "indigo" : "gray"}>
              {answer.selected ? "Selected winner" : "Candidate answer"}
            </Pill>

            <p className={"answer-body" + (expanded ? " open" : "")}>
              {answer.text}
            </p>

            <button
              type="button"
              className="link-button"
              onClick={() =>
                setOpen((state) => ({
                  ...state,
                  [answer.model]: !expanded,
                }))
              }
            >
              {expanded ? "Collapse answer ^" : "Expand full answer v"}
            </button>
          </div>
        );
      })}
    </div>
  );
}

function ScoresTab({ result }) {
  const [model, setModel] = useState(result.winning_model);

  const answer =
    result.answers.find((item) => item.model === model) || result.answers[0];

  return (
    <>
      <div className="two-col">
        <div className="card">
          <div className="card-title-row">
            <h3 className="card-title">Quality criteria</h3>
            <div className="chips">
              {result.answers.map((item) => (
                <button
                  key={item.model}
                  type="button"
                  className={"chip" + (item.model === answer.model ? " on" : "")}
                  onClick={() => setModel(item.model)}
                >
                  {item.model}
                </button>
              ))}
            </div>
          </div>

          {Object.keys(answer.criteria).length === 0 ? (
            <p className="muted">This answer could not be judged.</p>
          ) : (
            CRITERIA.map(([key, label]) => (
              <BarRow
                key={key}
                label={label}
                value={answer.criteria[key] ?? 0}
              />
            ))
          )}
        </div>

        <div className="card">
          <h3 className="card-title">Model agreement</h3>
          <Heatmap
            models={result.similarity.models}
            matrix={result.similarity.matrix}
          />
        </div>
      </div>

      <div className="card section-gap">
        <h3 className="card-title">How the trust score is built</h3>
        <ContributionBar weights={result.weights} scores={result.scores} />

        <div className="verifier-note">
          <strong>Verifier says</strong>
          <span>
            {result.verification.reason || "No explanation returned."}
          </span>
          {result.verification.confidence !== null &&
            result.verification.confidence !== undefined && (
              <em>Confidence {Math.round(result.verification.confidence)}%</em>
            )}
        </div>
      </div>
    </>
  );
}

function ClaimsTab({ result }) {
  const [openIndex, setOpenIndex] = useState(null);
  const summary = result.claims_summary;

  return (
    <div className="two-col claims-layout">
      <div className="card claims-card">
        <div className="card-title-row">
          <h3 className="card-title">Claim audit</h3>
          <Pill tone={summary.supported === summary.total ? "green" : "amber"}>
            {summary.supported} / {summary.total} supported
          </Pill>
        </div>

        {result.claims.length === 0 ? (
          <p className="muted">No claims were extracted.</p>
        ) : (
          <div className="claims-table" role="table">
            <div className="claims-head" role="row">
              <span>Claim</span>
              <span>Status</span>
              <span>Confidence</span>
              <span>Sources</span>
            </div>

            {result.claims.map((claim, index) => {
              const meta = STATUS_META[claim.status] || {
                label: claim.status,
                tone: "gray",
              };
              const open = openIndex === index;

              return (
                <div className="claim-item" key={index}>
                  <button
                    type="button"
                    className="claim-row"
                    onClick={() => setOpenIndex(open ? null : index)}
                    aria-expanded={open}
                  >
                    <span className="claim-text">{claim.claim}</span>
                    <span>
                      <Pill tone={meta.tone}>{meta.label.toUpperCase()}</Pill>
                    </span>
                    <span className="claim-conf">{Math.round(claim.confidence)}%</span>
                    <span className="claim-links">
                      {claim.sources.length} link
                      {claim.sources.length === 1 ? "" : "s"}
                    </span>
                  </button>

                  {open && (
                    <div className="claim-detail">
                      <strong>
                        Why this claim is {meta.label.toLowerCase()}
                      </strong>
                      <p>{claim.reason || "No explanation was returned."}</p>

                      {claim.sources.map((source, sourceIndex) => (
                        <div className="source" key={sourceIndex}>
                          <p>{source.snippet}</p>
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noreferrer noopener"
                          >
                            {source.title || source.url} ↗
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <p className="hint">
          Click a claim to expand reasoning, source snippets, and direct
          citations.
        </p>
      </div>

      <div className="card">
        <h3 className="card-title">Claim distribution</h3>
        <ClaimDonut summary={summary} />
      </div>
    </div>
  );
}
