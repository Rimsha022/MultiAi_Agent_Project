import {
  Document,
  Font,
  Link,
  Page,
  StyleSheet,
  Text,
  View,
} from "@react-pdf/renderer";

import { STATUS_META, fmt, formatDate, trustLabel } from "../utils.js";

// Keep long words/URLs intact instead of breaking them mid-word.
Font.registerHyphenationCallback((word) => [word]);

const C = {
  navy: "#17284A",
  navy2: "#22365F",
  indigo: "#5B6EF0",
  indigoSoft: "#ECEFFE",
  green: "#12A67B",
  greenSoft: "#DFF6EE",
  amber: "#C98515",
  amberSoft: "#FFF0D6",
  red: "#E0524D",
  redSoft: "#FDE6E5",
  grayText: "#7A87A3",
  graySoft: "#EAEEF6",
  line: "#E6EAF3",
  bg: "#F4F6FB",
};

const TONES = {
  green: { fg: C.green, bg: C.greenSoft },
  amber: { fg: C.amber, bg: C.amberSoft },
  red: { fg: C.red, bg: C.redSoft },
  gray: { fg: C.grayText, bg: C.graySoft },
  indigo: { fg: C.indigo, bg: C.indigoSoft },
};

const scoreTone = (value) =>
  value === null || value === undefined
    ? "gray"
    : value >= 8
    ? "green"
    : value >= 6
    ? "amber"
    : "red";

const trustTone = (level) =>
  level === "HIGH TRUST" ? "green" : level === "MODERATE TRUST" ? "amber" : "red";

// Standard PDF fonts only cover Latin text; swap or drop anything else.
function clean(text) {
  return String(text ?? "")
    .replace(/[→➔]/g, "->")
    .replace(/[✓✔]/g, "")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/ /g, " ")
    .replace(/[*_`#]+/g, "")
    .replace(/[^\n\x20-\x7E¡-ÿ–—•…€]/g, "");
}

const s = StyleSheet.create({
  page: {
    paddingTop: 54,
    paddingBottom: 54,
    paddingHorizontal: 38,
    fontFamily: "Helvetica",
    fontSize: 10,
    color: C.navy,
    backgroundColor: "#FFFFFF",
    lineHeight: 1.45,
  },
  runningHeader: {
    position: "absolute",
    top: 20,
    left: 38,
    right: 38,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: C.line,
    paddingBottom: 8,
  },
  brandRow: { flexDirection: "row", alignItems: "center" },
  brandMark: {
    width: 18,
    height: 18,
    borderRadius: 5,
    backgroundColor: C.indigo,
    color: "#FFFFFF",
    textAlign: "center",
    fontFamily: "Helvetica-Bold",
    fontSize: 10,
    paddingTop: 3,
    marginRight: 7,
  },
  brandName: { fontFamily: "Helvetica-Bold", fontSize: 10, letterSpacing: 1 },
  brandSub: { color: C.grayText, fontSize: 9, marginLeft: 4 },
  headerMeta: { fontSize: 8.5, color: C.grayText },
  footer: {
    position: "absolute",
    bottom: 22,
    left: 38,
    right: 38,
    flexDirection: "row",
    justifyContent: "space-between",
    fontSize: 8,
    color: C.grayText,
  },

  title: { fontFamily: "Helvetica-Bold", fontSize: 25, letterSpacing: -0.4 },
  subtitle: { color: C.grayText, marginTop: 3, marginBottom: 14 },
  eyebrow: {
    fontFamily: "Helvetica-Bold",
    fontSize: 7.5,
    letterSpacing: 1.1,
    textTransform: "uppercase",
    color: C.grayText,
  },
  questionBox: {
    backgroundColor: C.bg,
    borderRadius: 10,
    padding: 12,
    marginBottom: 14,
  },
  questionText: { fontFamily: "Helvetica-Bold", fontSize: 12, marginTop: 4 },

  topRow: { flexDirection: "row", marginBottom: 12 },
  trustCard: {
    width: 170,
    backgroundColor: C.navy,
    borderRadius: 14,
    padding: 16,
    marginRight: 12,
    justifyContent: "space-between",
  },
  trustNumRow: { flexDirection: "row", alignItems: "flex-end", marginTop: 10 },
  trustNum: { color: "#FFFFFF", fontFamily: "Helvetica-Bold", fontSize: 54, lineHeight: 1 },
  trustOf: { color: "#AAB6D3", fontSize: 12, marginLeft: 6, marginBottom: 6 },
  trustClaims: { color: "#C4CDE4", fontSize: 9, marginTop: 10 },

  answerCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: C.line,
    borderRadius: 14,
    padding: 16,
  },
  answerHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  answerText: { marginTop: 8, fontSize: 10.5, lineHeight: 1.6 },
  correction: { color: "#8A5A10", fontSize: 9, marginTop: 6 },
  answerFoot: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: C.line,
    color: C.grayText,
    fontSize: 8.5,
  },

  pill: {
    fontFamily: "Helvetica-Bold",
    fontSize: 7,
    letterSpacing: 0.6,
    textTransform: "uppercase",
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 99,
    alignSelf: "flex-start",
  },

  scoreRow: { flexDirection: "row", marginBottom: 6 },
  scoreCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: C.line,
    borderRadius: 12,
    padding: 12,
    marginRight: 8,
  },
  scoreVal: { fontFamily: "Helvetica-Bold", fontSize: 22, marginTop: 5 },
  scoreOf: { fontSize: 9, color: C.grayText },

  h2: { fontFamily: "Helvetica-Bold", fontSize: 14, marginTop: 20, marginBottom: 8 },
  card: { borderWidth: 1, borderColor: C.line, borderRadius: 12, padding: 14 },
  twoCol: { flexDirection: "row" },

  barRow: { flexDirection: "row", alignItems: "center", marginBottom: 7 },
  barLabel: { width: 84, fontSize: 9 },
  barTrack: { flex: 1, height: 6, borderRadius: 3, backgroundColor: C.graySoft },
  barFill: { height: 6, borderRadius: 3, backgroundColor: C.indigo },
  barVal: { width: 26, textAlign: "right", fontSize: 9, color: C.grayText },

  stack: { flexDirection: "row", height: 10, borderRadius: 5, overflow: "hidden", backgroundColor: C.graySoft },
  legend: { flexDirection: "row", flexWrap: "wrap", marginTop: 8 },
  legendItem: { flexDirection: "row", alignItems: "center", marginRight: 14, marginBottom: 3 },
  legendDot: { width: 7, height: 7, borderRadius: 4, marginRight: 4 },
  legendText: { fontSize: 8.5, color: C.grayText },

  heatRow: { flexDirection: "row", marginBottom: 4 },
  heatLabel: { width: 54, fontSize: 8.5, color: C.grayText, paddingTop: 5 },
  heatCell: {
    flex: 1,
    marginRight: 4,
    borderRadius: 6,
    paddingVertical: 5,
    textAlign: "center",
    fontFamily: "Helvetica-Bold",
    fontSize: 9,
  },
  heatHead: { flex: 1, marginRight: 4, textAlign: "center", fontSize: 7.5, color: C.grayText },

  tableHead: {
    flexDirection: "row",
    backgroundColor: "#EEF2F8",
    borderRadius: 8,
    paddingVertical: 7,
    paddingHorizontal: 10,
  },
  th: { fontFamily: "Helvetica-Bold", fontSize: 7.5, letterSpacing: 0.9, textTransform: "uppercase", color: C.grayText },
  claimItem: { borderBottomWidth: 1, borderBottomColor: C.line, paddingVertical: 9, paddingHorizontal: 10 },
  claimRow: { flexDirection: "row", alignItems: "flex-start" },
  claimText: { flex: 1, fontSize: 10, paddingRight: 8 },
  claimStatus: { width: 84 },
  claimConf: { width: 52, fontFamily: "Helvetica-Bold", textAlign: "right" },
  reason: { marginTop: 5, fontSize: 9, color: C.grayText },
  source: { marginTop: 3, fontSize: 8, color: C.indigo, textDecoration: "none" },

  modelCard: { borderWidth: 1, borderColor: C.line, borderRadius: 12, padding: 14, marginBottom: 10 },
  modelSelected: { borderColor: C.indigo, borderWidth: 1.5 },
  modelHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  modelName: { fontFamily: "Helvetica-Bold", fontSize: 12 },
  modelText: { fontSize: 9.5, lineHeight: 1.55 },
});

function Pill({ tone = "indigo", children }) {
  const colors = TONES[tone] || TONES.indigo;
  return (
    <Text style={[s.pill, { color: colors.fg, backgroundColor: colors.bg }]}>
      {children}
    </Text>
  );
}

function Bar({ label, value }) {
  return (
    <View style={s.barRow} wrap={false}>
      <Text style={s.barLabel}>{label}</Text>
      <View style={s.barTrack}>
        <View style={[s.barFill, { width: `${Math.max(0, Math.min(100, (value / 10) * 100))}%` }]} />
      </View>
      <Text style={s.barVal}>{fmt(value)}</Text>
    </View>
  );
}

const CRITERIA = [
  ["relevance", "Relevance"],
  ["completeness", "Completeness"],
  ["justification", "Justification"],
  ["context_awareness", "Context"],
  ["conciseness", "Conciseness"],
];

const COMPONENTS = [
  ["quality", "Quality", C.indigo],
  ["verification", "Verification", C.navy],
  ["evidence", "Evidence", C.green],
  ["consistency", "Consistency", "#E8A33D"],
];

export default function ReportPdf({ run }) {
  const result = run.result;
  const summary = result.claims_summary;
  const winner =
    result.answers.find((answer) => answer.selected) || result.answers[0];

  const contributions = COMPONENTS.filter(
    ([key]) => result.weights[key] !== undefined && result.scores[key] !== null
  ).map(([key, label, color]) => ({
    key,
    label,
    color,
    weight: result.weights[key],
    points: result.weights[key] * result.scores[key],
  }));
  const totalPoints = contributions.reduce((sum, item) => sum + item.points, 0) || 1;

  const date = formatDate(run.finished_at || run.created_at);

  return (
    <Document
      title={`Verity AI report ${run.id}`}
      author="Verity AI"
      subject={clean(run.question)}
    >
      <Page size="A4" style={s.page}>
        {/* running header and footer */}
        <View style={s.runningHeader} fixed>
          <View style={s.brandRow}>
            <Text style={s.brandMark}>V</Text>
            <Text style={s.brandName}>VERITY</Text>
            <Text style={s.brandSub}>/ AI</Text>
          </View>
          <Text style={s.headerMeta}>
            Run {run.id}  |  {date}
          </Text>
        </View>

        <View style={s.footer} fixed>
          <Text>Verity AI - multi-model answer validation</Text>
          <Text
            render={({ pageNumber, totalPages }) =>
              `Page ${pageNumber} of ${totalPages}`
            }
          />
        </View>

        {/* title + question */}
        <Text style={s.title}>Verification report</Text>
        <Text style={s.subtitle}>
          A clear verdict first. Evidence and scoring follow.
        </Text>

        <View style={s.questionBox}>
          <Text style={s.eyebrow}>Question</Text>
          <Text style={s.questionText}>{clean(run.question.trim())}</Text>
        </View>

        {!result.valid && (
          <View style={[s.questionBox, { backgroundColor: C.amberSoft }]}>
            <Text style={{ color: "#8A5A10", fontSize: 9 }}>
              Incomplete validation: {clean(result.validation_errors.join(" | "))}
            </Text>
          </View>
        )}

        {/* verdict */}
        <View style={s.topRow}>
          <View style={s.trustCard}>
            <View>
              <Text style={[s.eyebrow, { color: "#AAB6D3" }]}>Trust index</Text>
              <View style={s.trustNumRow}>
                <Text style={s.trustNum}>{fmt(result.trust_score)}</Text>
                <Text style={s.trustOf}>/ 10</Text>
              </View>
            </View>
            <View>
              <Pill tone={trustTone(result.trust_level)}>
                {trustLabel(result.trust_level)}
              </Pill>
              <Text style={s.trustClaims}>
                {summary.supported} / {summary.total} claims supported
              </Text>
            </View>
          </View>

          <View style={s.answerCard}>
            <View style={s.answerHead}>
              <Text style={[s.eyebrow, { color: C.indigo }]}>Verified answer</Text>
              {result.corrections.length > 0 && (
                <Pill tone="amber">
                  {result.corrections.length} correction
                  {result.corrections.length > 1 ? "s" : ""}
                </Pill>
              )}
            </View>
            <Text style={s.answerText}>{clean(result.verified_answer)}</Text>
            {result.corrections.map((item, index) => (
              <Text key={index} style={s.correction}>
                - {clean(item)}
              </Text>
            ))}
            <Text style={s.answerFoot}>
              Winning model: {result.winning_model.toUpperCase()}  |  {result.models_compared} models compared
            </Text>
          </View>
        </View>

        {/* score cards */}
        <View style={s.scoreRow} wrap={false}>
          {[
            ["Quality", result.scores.quality],
            ["Consistency", result.scores.consistency],
            ["Verification", result.scores.verification],
            ["Evidence", result.scores.evidence],
          ].map(([label, value], index, list) => (
            <View
              key={label}
              style={[s.scoreCard, index === list.length - 1 ? { marginRight: 0 } : {}]}
            >
              <Text style={s.eyebrow}>{label}</Text>
              <Text style={[s.scoreVal, { color: TONES[scoreTone(value)].fg }]}>
                {fmt(value)} <Text style={s.scoreOf}>/ 10</Text>
              </Text>
            </View>
          ))}
        </View>

        {/* scoring breakdown */}
        <Text style={s.h2} minPresenceAhead={90}>How the trust score is built</Text>
        <View style={s.card} wrap={false}>
          <View style={s.stack}>
            {contributions.map((item) => (
              <View
                key={item.key}
                style={{
                  width: `${(item.points / totalPoints) * 100}%`,
                  backgroundColor: item.color,
                }}
              />
            ))}
          </View>
          <View style={s.legend}>
            {contributions.map((item) => (
              <View key={item.key} style={s.legendItem}>
                <View style={[s.legendDot, { backgroundColor: item.color }]} />
                <Text style={s.legendText}>
                  {item.label} {Math.round(item.weight * 100)}% (+{fmt(item.points, 2)})
                </Text>
              </View>
            ))}
          </View>
          {result.verification.reason ? (
            <Text style={[s.reason, { marginTop: 8 }]}>
              Verifier: {clean(result.verification.reason)}
              {result.verification.confidence !== null &&
              result.verification.confidence !== undefined
                ? ` (confidence ${Math.round(result.verification.confidence)}%)`
                : ""}
            </Text>
          ) : null}
        </View>

        {/* criteria + agreement */}
        <View style={[s.twoCol, { marginTop: 12 }]} wrap={false}>
          <View style={[s.card, { flex: 1, marginRight: 10 }]}>
            <Text style={[s.eyebrow, { marginBottom: 8 }]}>
              Quality criteria - {winner.model}
            </Text>
            {CRITERIA.map(([key, label]) => (
              <Bar key={key} label={label} value={winner.criteria[key] ?? 0} />
            ))}
          </View>

          <View style={[s.card, { flex: 1 }]}>
            <Text style={[s.eyebrow, { marginBottom: 8 }]}>Model agreement</Text>
            <View style={s.heatRow}>
              <Text style={s.heatLabel} />
              {result.similarity.models.map((model) => (
                <Text key={model} style={s.heatHead}>
                  {model}
                </Text>
              ))}
            </View>
            {result.similarity.models.map((model, row) => (
              <View key={model} style={s.heatRow}>
                <Text style={s.heatLabel}>{model}</Text>
                {result.similarity.matrix[row].map((value, col) => (
                  <Text
                    key={col}
                    style={[
                      s.heatCell,
                      { backgroundColor: `rgba(91,110,240,${0.1 + value * 0.35})` },
                    ]}
                  >
                    {Math.round(value * 100)}%
                  </Text>
                ))}
              </View>
            ))}
          </View>
        </View>

        {/* claims */}
        <Text style={s.h2} minPresenceAhead={120}>
          Claims & evidence
        </Text>
        <View style={{ flexDirection: "row", marginBottom: 8 }}>
          <Pill tone={summary.supported === summary.total ? "green" : "amber"}>
            {summary.supported} / {summary.total} supported
          </Pill>
          <Text style={{ marginLeft: 8, color: C.grayText, fontSize: 9, paddingTop: 3 }}>
            {summary.contradicted} contradicted | {summary.insufficient} insufficient
            {summary.errors ? ` | ${summary.errors} errors` : ""}
          </Text>
        </View>

        <View style={s.tableHead} wrap={false}>
          <Text style={[s.th, { flex: 1 }]}>Claim</Text>
          <Text style={[s.th, { width: 84 }]}>Status</Text>
          <Text style={[s.th, { width: 52, textAlign: "right" }]}>Conf.</Text>
        </View>

        {result.claims.length === 0 && (
          <Text style={[s.reason, { padding: 10 }]}>No claims were extracted.</Text>
        )}

        {result.claims.map((claim, index) => {
          const meta = STATUS_META[claim.status] || { label: claim.status, tone: "gray" };
          return (
            <View key={index} style={s.claimItem} wrap={false}>
              <View style={s.claimRow}>
                <Text style={s.claimText}>{clean(claim.claim)}</Text>
                <View style={s.claimStatus}>
                  <Pill tone={meta.tone}>{meta.label}</Pill>
                </View>
                <Text style={s.claimConf}>{Math.round(claim.confidence)}%</Text>
              </View>
              {claim.reason ? <Text style={s.reason}>{clean(claim.reason)}</Text> : null}
              {claim.sources.map((source, sourceIndex) => (
                <Link key={sourceIndex} src={source.url} style={s.source}>
                  {clean(source.title || source.url)}  -  {clean(source.url)}
                </Link>
              ))}
            </View>
          );
        })}

        {/* model answers */}
        <Text style={s.h2} minPresenceAhead={120}>
          Model answers
        </Text>
        {result.answers.map((answer) => (
          <View
            key={answer.model}
            style={[s.modelCard, answer.selected ? s.modelSelected : {}]}
          >
            <View style={s.modelHead} wrap={false}>
              <View style={{ flexDirection: "row", alignItems: "center" }}>
                <Text style={s.modelName}>{answer.model}</Text>
                <View style={{ marginLeft: 8 }}>
                  <Pill tone={answer.selected ? "indigo" : "gray"}>
                    {answer.selected ? "Selected winner" : "Candidate"}
                  </Pill>
                </View>
              </View>
              <Text
                style={{
                  fontFamily: "Helvetica-Bold",
                  fontSize: 13,
                  color: TONES[scoreTone(answer.quality)].fg,
                }}
              >
                {fmt(answer.quality)} / 10
              </Text>
            </View>
            <Text style={s.modelText}>{clean(answer.text)}</Text>
          </View>
        ))}
      </Page>
    </Document>
  );
}
