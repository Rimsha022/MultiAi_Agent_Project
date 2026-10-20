export function trustTone(level) {
  if (level === "HIGH TRUST") return "green";
  if (level === "MODERATE TRUST") return "amber";
  return "red";
}

export function scoreTone(score) {
  if (score === null || score === undefined) return "amber";
  if (score >= 8) return "green";
  if (score >= 6) return "amber";
  return "red";
}

export const trustLabel = (level) =>
  (level || "").replace(" TRUST", "") + " TRUST";

export function fmt(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "–";
  }
  return Number(value).toFixed(digits);
}

export function formatDate(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export const STATUS_META = {
  SUPPORTED: { label: "Supported", tone: "green" },
  CONTRADICTED: { label: "Contradicted", tone: "red" },
  INSUFFICIENT_EVIDENCE: { label: "Insufficient", tone: "amber" },
  ERROR: { label: "Error", tone: "red" },
};

export function buildCitation(run) {
  const result = run.result;
  const date = formatDate(run.finished_at || run.created_at);

  return (
    `Verity AI. "${run.question.trim()}" Trust score ` +
    `${fmt(result.trust_score)}/10 (${trustLabel(result.trust_level)}); ` +
    `${result.claims_summary.supported}/${result.claims_summary.total} claims supported. ` +
    `Validated ${date}. Run ${run.id}.`
  );
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
