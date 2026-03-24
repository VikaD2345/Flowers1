import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import PublicApp from "./PublicApp";
import { AdminApp } from "./admin/AdminApp";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PublicApp />} />
      <Route path="/admin/*" element={<AdminApp />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
