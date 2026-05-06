import { Navigate, Route, Routes } from "react-router-dom";

import NewSession from "./pages/NewSession";
import QueryResult from "./pages/QueryResult";
import ReviewPage from "./pages/ReviewPage";
import SessionHome from "./pages/SessionHome";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/session/new" replace />} />
      <Route path="/session/new" element={<NewSession />} />
      <Route path="/session/:sessionId" element={<SessionHome />} />
      <Route path="/session/:sessionId/query/:queryId" element={<QueryResult />} />
      <Route
        path="/session/:sessionId/query/:queryId/review"
        element={<ReviewPage />}
      />
    </Routes>
  );
}
