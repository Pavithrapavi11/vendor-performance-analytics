import { useState } from "react";
import { api } from "@/api";
import { ANALYTICS } from "@/constants/testIds";

/* Upload dialog — three required CSVs, one optional (products) plus name. */
export function UploadDialog({ onClose, onUploaded }) {
  const [files, setFiles] = useState({
    vendors: null,
    purchase_orders: null,
    quality_inspections: null,
    products: null,
  });
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const setFile = (k) => (e) =>
    setFiles((prev) => ({ ...prev, [k]: e.target.files?.[0] || null }));

  const canSubmit =
    files.vendors && files.purchase_orders && files.quality_inspections && !busy;

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("vendors", files.vendors);
      fd.append("purchase_orders", files.purchase_orders);
      fd.append("quality_inspections", files.quality_inspections);
      if (files.products) fd.append("products", files.products);
      if (name.trim()) fd.append("name", name.trim());
      const r = await api.post("/analytics/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onUploaded(r.data);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const req = (label, key, required = true) => (
    <label className="nb-upload__field" key={key}>
      <div className="nb-upload__label">
        {label}.csv {required && <span className="nb-upload__req">*</span>}
      </div>
      <input
        type="file"
        accept=".csv,text/csv"
        onChange={setFile(key)}
        data-testid={`upload-file-${key}`}
      />
      {files[key] && (
        <div className="nb-upload__ok">
          {files[key].name} &middot;{" "}
          {(files[key].size / 1024).toFixed(1)} KB
        </div>
      )}
    </label>
  );

  return (
    <div
      className="nb-modal__scrim"
      role="dialog"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      data-testid={ANALYTICS.uploadDialog}
    >
      <div className="nb-modal">
        <header className="nb-modal__head">
          <h3>Upload your dataset</h3>
          <button
            className="nb-modal__close"
            onClick={onClose}
            aria-label="Close"
            data-testid={ANALYTICS.uploadDialogClose}
          >
            ×
          </button>
        </header>

        <p className="nb-modal__desc">
          The analysis needs three CSVs (products is optional). Column names
          must match the schema below — see the &ldquo;Data schema&rdquo; drawer for the
          full list. The demo dataset in this repo is a valid example.
        </p>

        <label className="nb-upload__field">
          <div className="nb-upload__label">Dataset name</div>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Acme Ltd — Q3 2025"
            data-testid={ANALYTICS.uploadName}
          />
        </label>

        {req("vendors", "vendors")}
        {req("purchase_orders", "purchase_orders")}
        {req("quality_inspections", "quality_inspections")}
        {req("products (optional)", "products", false)}

        {err && (
          <div className="nb-modal__error" data-testid={ANALYTICS.uploadError}>
            {err}
          </div>
        )}

        <footer className="nb-modal__foot">
          <button className="nb-btn nb-btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            className="nb-btn nb-btn--primary"
            onClick={submit}
            disabled={!canSubmit}
            data-testid={ANALYTICS.uploadSubmit}
          >
            {busy ? "Running analysis…" : "Run analysis on this dataset"}
          </button>
        </footer>
      </div>
    </div>
  );
}

/* Schema drawer — lists required columns so uploads succeed. */
export function SchemaDrawer({ schema, onClose }) {
  return (
    <div
      className="nb-modal__scrim"
      role="dialog"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      data-testid={ANALYTICS.schemaDialog}
    >
      <div className="nb-modal">
        <header className="nb-modal__head">
          <h3>Data schema</h3>
          <button className="nb-modal__close" onClick={onClose}>×</button>
        </header>
        <p className="nb-modal__desc">
          Column names must match exactly. Dates must parse as YYYY-MM-DD.
        </p>
        {Object.entries(schema.columns).map(([table, cols]) => (
          <div key={table} className="nb-schema__group">
            <div className="nb-schema__title">{table}.csv</div>
            <div className="nb-schema__cols">
              {cols.map((c) => (
                <code key={c} className="nb-schema__col">{c}</code>
              ))}
            </div>
          </div>
        ))}
        <div className="nb-schema__notes">
          {schema.notes.map((n) => <div key={n}>• {n}</div>)}
        </div>
      </div>
    </div>
  );
}
