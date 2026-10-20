// Builds the report PDF on demand. The PDF library is loaded lazily so it
// only downloads when someone actually exports.
export async function exportReportPdf(run) {
  const [{ pdf }, { default: ReportPdf }] = await Promise.all([
    import("@react-pdf/renderer"),
    import("./ReportPdf.jsx"),
  ]);

  const blob = await pdf(<ReportPdf run={run} />).toBlob();
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = `verity-report-${run.id}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
