import { createContext, useContext, useState } from "react";
import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout.jsx";
import AskPage from "./pages/AskPage.jsx";
import RunPage from "./pages/RunPage.jsx";
import ReportPage from "./pages/ReportPage.jsx";
import DetailsPage from "./pages/DetailsPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

// Lets the top-bar Export button know which report is open.
const ReportContext = createContext({ report: null, setReport: () => {} });

export const useReportContext = () => useContext(ReportContext);

export default function App() {
  const [report, setReport] = useState(null);

  return (
    <ReportContext.Provider value={{ report, setReport }}>
      <Layout>
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/run/:id" element={<RunPage />} />
          <Route path="/report/:id" element={<ReportPage />} />
          <Route path="/report/:id/:tab" element={<DetailsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<AskPage />} />
        </Routes>
      </Layout>
    </ReportContext.Provider>
  );
}
