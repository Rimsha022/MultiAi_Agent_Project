import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getRun } from "./api.js";
import { useReportContext } from "./App.jsx";

// Loads a finished run and registers it for the top-bar Export button.
export function useReport(id) {
  const navigate = useNavigate();
  const { setReport } = useReportContext();

  const [run, setRun] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    setRun(null);
    setError("");

    getRun(id)
      .then((data) => {
        if (cancelled) return;

        if (data.status === "running") {
          navigate(`/run/${id}`, { replace: true });
          return;
        }

        setRun(data);
        setReport(data.result ? data : null);
      })
      .catch((err) => !cancelled && setError(err.message));

    return () => {
      cancelled = true;
      setReport(null);
    };
  }, [id, navigate, setReport]);

  return { run, error };
}
