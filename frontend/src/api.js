import { useEffect, useState } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 60000 });

// Small helpers used across the dashboard
export const inrCr = (n) =>
  n == null ? "—" : `\u20B9${(Number(n) / 1e7).toFixed(2)} Cr`;
export const pct = (n, d = 1) =>
  n == null || Number.isNaN(Number(n)) ? "—" : `${Number(n).toFixed(d)}%`;
export const num = (n, d = 1) =>
  n == null || Number.isNaN(Number(n)) ? "—" : Number(n).toFixed(d);
export const fmtInt = (n) =>
  n == null ? "—" : Number(n).toLocaleString();

export function useAnalytics(datasetId) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!datasetId) return;
    setLoading(true);
    setErr(null);
    api
      .get(`/analytics/${datasetId}/summary`)
      .then((r) => setData(r.data))
      .catch((e) =>
        setErr(e.response?.data?.detail || e.message || "Failed to load")
      )
      .finally(() => setLoading(false));
  }, [datasetId]);

  return { data, err, loading };
}

export function useDatasets() {
  const [datasets, setDatasets] = useState([]);
  const refresh = () =>
    api.get("/analytics/datasets").then((r) => setDatasets(r.data.datasets));
  useEffect(() => {
    refresh();
  }, []);
  return { datasets, refresh };
}
