import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getRun } from "../api.js";
import { ErrorBlock, LoadingBlock, Notice, PageHeader, Pill } from "../components/ui.jsx";

const MODEL_DOT = {
  queued: "dot-idle",
  generating: "dot-indigo",
  responded: "dot-green",
  rate_limited: "dot-amber",
  failed: "dot-red",
};

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function RunPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [run, setRun] = useState(null);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const failures = useRef(0);

  useEffect(() => {
    let cancelled = false;
    let timer;

    async function poll() {
      try {
        const data = await getRun(id);
        if (cancelled) return;

        failures.current = 0;
        setRun(data);

        if (data.status === "done") {
          setTimeout(() => navigate(`/report/${id}`, { replace: true }), 900);
          return;
        }
        if (data.status === "error") return;
      } catch (err) {
        if (cancelled) return;
        failures.current += 1;

        if (failures.current >= 5) {
          setError(err.message);
          return;
        }
      }

      timer = setTimeout(poll, 1500);
    }

    poll();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, navigate]);

  useEffect(() => {
    if (!run || run.status !== "running") return undefined;

    const start = new Date(run.created_at).getTime();
    const tick = setInterval(
      () => setElapsed(Math.max(0, Math.round((Date.now() - start) / 1000))),
      1000
    );

    return () => clearInterval(tick);
  }, [run]);

  if (error) {
    return (
      <ErrorBlock
        title="Lost connection to the backend"
        message={error}
        action={<Link className="btn btn-primary" to="/">Back to Ask</Link>}
      />
    );
  }

  if (!run) return <LoadingBlock label="Connecting to your run…" />;

  const running = run.status === "running";
  const failed = run.status === "error";

  return (
    <>
      <PageHeader
        title={failed ? "Verification stopped" : "Verification in progress"}
        subtitle="Six transparent steps from model generation to evidence review."
      />

      <div className="ask-grid">
        <div className="card run-card">
          <div className="run-head">
            <span className="eyebrow">Run / {run.id}</span>
            <Pill tone={failed ? "red" : running ? "amber" : "green"}>
              {failed ? "Failed" : running ? `Analyzing · ${formatElapsed(elapsed)}` : "Complete"}
            </Pill>
          </div>

          <p className="run-question">{run.question}</p>

          <ol className="stepper">
            {run.stages.map((stage, index) => (
              <li key={stage.key} className={`step step-${stage.status}`}>
                <span className="step-mark">
                  {stage.status === "complete"
                    ? "✓"
                    : stage.status === "error"
                    ? "!"
                    : index + 1}
                </span>
                <span className="step-label">
                  {stage.label}
                  {stage.detail && stage.status !== "queued" && (
                    <small>{stage.detail}</small>
                  )}
                </span>
                <span className="step-state">
                  {stage.status === "in_progress"
                    ? "IN PROGRESS"
                    : stage.status === "error"
                    ? "FAILED"
                    : stage.status.toUpperCase()}
                </span>
              </li>
            ))}
          </ol>
        </div>

        <aside className="card card-navy model-status">
          <div className="eyebrow light">Model status</div>

          {Object.entries(run.models).map(([name, info]) => (
            <div className="model-chip" key={name}>
              <div>
                <strong>{name}</strong>
                <small>{info.detail}</small>
              </div>
              <span className={`dot-lg ${MODEL_DOT[info.status] || "dot-idle"}`} />
            </div>
          ))}
        </aside>
      </div>

      {failed && (
        <ErrorBlock
          title="This validation could not be completed"
          message={run.error}
          action={<Link className="btn btn-primary" to="/">Try another question</Link>}
        />
      )}

      {run.notices.map((notice, index) => (
        <Notice
          key={index}
          level={notice.level}
          title={notice.title}
          message={notice.message}
        />
      ))}

      <Notice
        level="warning"
        title="Resilience state"
        message="Model timeouts and rate limits are visible; failed models never silently disappear."
      />
    </>
  );
}
