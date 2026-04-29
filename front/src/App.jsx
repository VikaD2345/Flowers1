import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import PublicApp from "./PublicApp";
import { AdminApp } from "./admin/AdminApp";

export default function App() {
  useEffect(() => {
    const removeInjectedPopup = () => {
      document.querySelectorAll("#tr-popup").forEach((node) => node.remove());
    };

    removeInjectedPopup();

    const observer = new MutationObserver(() => {
      removeInjectedPopup();
    });

    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <Routes>
      <Route path="/" element={<PublicApp />} />
      <Route path="/admin/*" element={<AdminApp />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
