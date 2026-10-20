import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  getBenchmarkQuestions,
  getHealth,
  getHistory,
  startValidation,
} from "../api.js";
import { Notice, PageHeader, Pill } from "../components/ui.jsx";

const ENGINE_STEPS = [
  "Generate",
  "Compare",
  "Judge",
  "Verify",
  "Evidence",
  "Trust index",
];

export default function AskPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [mode, setMode] = useState(
    params.get("mode") === "benchmark" ? "benchmark" : "custom"
  );
  const [question, setQuestion] = useState("");
  const [benchmarks, setBenchmarks] = useState([]);
  const [category, setCategory] = useState("");
  const [benchmarkId, setBenchmarkId] = useState("");
  const [recent, setRecent] = useState([]);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch((err) =>
      setHealth({ ok: false, error: err.message })
    );

    getBenchmarkQuestions()
      .then((items) => {
        setBenchmarks(items);
        if (items.length) setCategory(items[0].category);
      })
      .catch(() => {});

    getHistory()
      .then((data) => setRecent(data.items.slice(0, 3)))
      .catch(() => {});
  }, []);

  const categories = useMemo(
    () => [...new Set(benchmarks.map((item) => item.category))],
    [benchmarks]
  );

  const categoryQuestions = useMemo(
    () => benchmarks.filter((item) => item.category === category),
    [benchmarks, category]
  );

  useEffect(() => {
    setBenchmarkId(categoryQuestions[0]?.id || "");
  }, [categoryQuestions]);

  const selectedBenchmark = categoryQuestions.find(
    (item) => item.id === benchmarkId
  );

  const finalQuestion =
    mode === "custom" ? question.trim() : selectedBenchmark?.question || "";

  async function submit(event) {
    event.preventDefault();

    if (!finalQuestion) {
      setError("Please enter a question to validate.");
      return;
    }

    setError("");
    setSubmitting(true);

    try {
      const { id } = await startValidation(
        finalQuestion,
        mode === "custom" ? "Manual" : category
      );
      navigate(`/run/${id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  const backendDown = health && !health.ok;

  return (
    <>
      <PageHeader
        title="Ask anything. Verify everything."
        subtitle="Multi-model intelligence with source-backed confidence."
      />

      {backendDown && (
        <Notice
          level="error"
          title="Backend unavailable"
          message={health.error || "Start the API on port 8000."}
        />
      )}

      <div className="ask-grid">
        <form className="card ask-card" onSubmit={submit}>
          <div className="ask-card-head">
            <span className="eyebrow accent">New validation</span>
            <Pill>{mode === "custom" ? "Custom question" : "Benchmark"}</Pill>
          </div>

          <div className="segmented">
            <button
              type="button"
              className={mode === "custom" ? "on" : ""}
              onClick={() => setMode("custom")}
            >
              Type your own question
            </button>
            <button
              type="button"
              className={mode === "benchmark" ? "on" : ""}
              onClick={() => setMode("benchmark")}
            >
              Benchmark library
            </button>
          </div>

          {mode === "custom" ? (
            <label className="question-box">
              <span>What would you like to validate?</span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="e.g. How do solar panels work on cloudy days?"
                rows={4}
                maxLength={1000}
              />
              <small>Answers are compared across up to three models.</small>
            </label>
          ) : (
            <div className="question-box">
              <div className="select-row">
                <label>
                  <span>Category</span>
                  <select
                    value={category}
                    onChange={(event) => setCategory(event.target.value)}
                  >
                    {categories.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Question</span>
                  <select
                    value={benchmarkId}
                    onChange={(event) => setBenchmarkId(event.target.value)}
                  >
                    {categoryQuestions.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.id} — {item.question}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <p className="picked-question">
                {selectedBenchmark?.question || "No benchmark questions found."}
              </p>
            </div>
          )}

          {error && <Notice level="error" title={error} />}

          <div className="ask-actions">
            <p className="hint">
              A full validation makes about 20 model calls and takes a few
              minutes.
            </p>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || backendDown || !finalQuestion}
            >
              {submitting ? "Starting…" : "Validate →"}
            </button>
          </div>
        </form>

        <aside className="card card-navy engine">
          <div className="eyebrow light">Verification engine</div>
          <ol>
            {ENGINE_STEPS.map((step, index) => (
              <li key={step}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                {step}
              </li>
            ))}
          </ol>
        </aside>
      </div>

      <section className="section">
        <div className="eyebrow">Recent research</div>

        {recent.length === 0 ? (
          <p className="muted">No validations yet. Your first one will appear here.</p>
        ) : (
          <div className="recent-grid">
            {recent.map((item) => (
              <div className="card recent-card" key={item.timestamp + item.question}>
                <h3>{item.question}</h3>
                {item.run_id ? (
                  <Link to={`/report/${item.run_id}`}>Open previous report →</Link>
                ) : (
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => {
                      setMode("custom");
                      setQuestion(item.question);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  >
                    Ask again →
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
