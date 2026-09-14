import { useEffect, useMemo, useState } from "react";
import "@/App.css";

import { api, useAnalytics, useDatasets, inrCr, pct, num, fmtInt } from "@/api";
import { KpiCard, VendorCard, Badge } from "@/components/atoms";
import { UploadDialog, SchemaDrawer } from "@/components/UploadDialog";
import {
  MonthlyTrendChart, DeliveryBucketsChart, CategoryChart,
} from "@/components/charts";
import { ANALYTICS } from "@/constants/testIds";

/* --------------------------------------------------------------------------
 *  Dashboard root — renders the entire analytics application.
 * ------------------------------------------------------------------------ */
export default function App() {
  const { datasets, refresh: refreshDatasets } = useDatasets();
  const [datasetId, setDatasetId] = useState("demo");
  const [showUpload, setShowUpload] = useState(false);
  const [showSchema, setShowSchema] = useState(false);
  const [schema, setSchema] = useState(null);
  const [filters, setFilters] = useState({ region: "All", category: "All" });

  useEffect(() => {
    api.get("/analytics/schema").then((r) => setSchema(r.data));
  }, []);

  const { data, err, loading } = useAnalytics(datasetId);

  const onUploaded = (dataset) => {
    setShowUpload(false);
    refreshDatasets().then(() => setDatasetId(dataset.id));
  };

  const activeDataset = datasets.find((d) => d.id === datasetId);
  const canDelete = activeDataset?.source === "upload";

  const deleteActive = async () => {
    if (!activeDataset || !canDelete) return;
    if (!window.confirm(`Delete "${activeDataset.name}"?`)) return;
    await api.delete(`/analytics/${datasetId}`);
    await refreshDatasets();
    setDatasetId("demo");
  };

  return (
    <div className="nb-shell">
      <Header
        datasets={datasets}
        datasetId={datasetId}
        setDatasetId={setDatasetId}
        onOpenUpload={() => setShowUpload(true)}
        onOpenSchema={() => setShowSchema(true)}
        canDelete={canDelete}
        onDelete={deleteActive}
      />

      {loading && (
        <div className="nb-loading" data-testid={ANALYTICS.loadingState}>
          Running analysis on <strong>{activeDataset?.name || datasetId}</strong>…
        </div>
      )}

      {err && !loading && (
        <div className="nb-error" data-testid={ANALYTICS.errorState}>
          {err}
        </div>
      )}

      {data && !loading && !err && (
        <Dashboard
          data={data}
          activeDataset={activeDataset}
          filters={filters}
          setFilters={setFilters}
        />
      )}

      {showUpload && (
        <UploadDialog
          onClose={() => setShowUpload(false)}
          onUploaded={onUploaded}
        />
      )}
      {showSchema && schema && (
        <SchemaDrawer schema={schema} onClose={() => setShowSchema(false)} />
      )}
    </div>
  );
}

/* --------------------------------------------------------------------------
 *  Sticky header with dataset selector + upload/schema controls.
 * ------------------------------------------------------------------------ */
function Header({
  datasets, datasetId, setDatasetId,
  onOpenUpload, onOpenSchema, canDelete, onDelete,
}) {
  return (
    <header className="nb-header" data-testid={ANALYTICS.appHeader}>
      <div className="nb-header__brand">
        <div className="nb-header__logo">NB</div>
        <div>
          <div className="nb-header__eyebrow">NorthBridge Supplies</div>
          <div className="nb-header__title">Vendor Performance Analytics</div>
        </div>
      </div>

      <div className="nb-header__controls">
        <label className="nb-picker">
          <span className="nb-picker__label">Dataset</span>
          <select
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            data-testid={ANALYTICS.datasetSelector}
          >
            {datasets.map((d) => (
              <option
                key={d.id}
                value={d.id}
                data-testid={ANALYTICS.datasetOption(d.id)}
              >
                {d.name}{d.source === "upload" ? " ↑" : ""}
              </option>
            ))}
          </select>
        </label>

        {canDelete && (
          <button
            className="nb-btn nb-btn--ghost nb-btn--danger"
            onClick={onDelete}
            data-testid={ANALYTICS.deleteDatasetBtn}
            title="Delete this uploaded dataset"
          >
            Delete
          </button>
        )}

        <button
          className="nb-btn nb-btn--ghost"
          onClick={onOpenSchema}
          data-testid={ANALYTICS.openSchemaBtn}
        >
          Data schema
        </button>

        <button
          className="nb-btn nb-btn--primary"
          onClick={onOpenUpload}
          data-testid={ANALYTICS.openUploadBtn}
        >
          Upload data →
        </button>
      </div>
    </header>
  );
}

/* --------------------------------------------------------------------------
 *  Everything below the header — rendered once data is loaded.
 * ------------------------------------------------------------------------ */
function Dashboard({ data, activeDataset, filters, setFilters }) {
  const {
    totals, averages, benchmarks, cleaning_log,
    leaderboard, pip, reward, category, monthly, delivery_buckets, decline,
  } = data;

  const pipIds    = pip.map((v) => v.vendor_id);
  const rewardIds = reward.map((v) => v.vendor_id);
  const vendorsById = useMemo(
    () => Object.fromEntries(leaderboard.map((v) => [v.vendor_id, v])),
    [leaderboard]
  );
  const focusVendor = pip[0] || reward[0] || leaderboard[0];
  const declineTop = decline[0];

  const regions    = useMemo(
    () => ["All", ...new Set(leaderboard.map((v) => v.region).filter(Boolean))],
    [leaderboard]
  );
  const categories = useMemo(
    () => ["All", ...new Set(leaderboard.map((v) => v.vendor_category).filter(Boolean))],
    [leaderboard]
  );

  const filtered = leaderboard
    .filter((v) => filters.region   === "All" || v.region          === filters.region)
    .filter((v) => filters.category === "All" || v.vendor_category === filters.category)
    .slice()
    .sort((a, b) => Number(b.composite_score) - Number(a.composite_score));

  return (
    <>
      {/* Hero */}
      <section className="nb-hero" data-testid={ANALYTICS.hero}>
        <div className="nb-hero__eyebrow">
          {activeDataset?.name || "Dataset"} &middot;{" "}
          {totals.earliest_order && totals.latest_order
            ? `${totals.earliest_order} → ${totals.latest_order}`
            : "date range unavailable"}{" "}
          &middot; INR
        </div>
        <h1 className="nb-hero__title">Vendor performance overview</h1>
        <p className="nb-hero__lede">
          {fmtInt(totals.total_pos)} POs across{" "}
          <strong>{totals.unique_vendors}</strong> vendors, analysed with the
          documented methodology — OTD, defect rate, price variance, lead
          time, fill rate, and a 40/40/20 composite score with a{" "}
          <strong>≥ 20 PO</strong> eligibility rule. The report supports the
          decision; sole-source and total-cost checks stay with the category
          manager.
        </p>
      </section>

      {/* KPI strip */}
      <section className="nb-kpis">
        <KpiCard label="Total POs"           value={fmtInt(totals.total_pos)}
                 tone="teal"  testId={ANALYTICS.kpiCardTotalPos} />
        <KpiCard label="Total spend"         value={inrCr(totals.total_spend_inr)}
                 tone="ink"   testId={ANALYTICS.kpiCardSpend} />
        <KpiCard label="Avg OTD %"           value={pct(averages.otd_pct)}
                 tone="teal"  testId={ANALYTICS.kpiCardAvgOtd} />
        <KpiCard label="Avg defect rate"     value={pct(averages.defect_rate_pct, 2)}
                 tone="coral" testId={ANALYTICS.kpiCardAvgDefect} />
        <KpiCard label="Avg vendor score"    value={num(averages.composite_score)}
                 tone="sand"  testId={ANALYTICS.kpiCardAvgScore} />
        <KpiCard label="Inspection coverage" value={pct(totals.inspection_coverage_pct)}
                 tone="ink"   testId={ANALYTICS.kpiCardCoverage} />
      </section>

      {/* PIP + Reward */}
      <section className="nb-two">
        <div className="nb-panel" data-testid={ANALYTICS.pipSection}>
          <div className="nb-panel__head">
            <Badge tone="coral">Recommended for PIP</Badge>
            <h2>Bottom 3 eligible vendors with an operational issue</h2>
            <p className="nb-panel__desc">
              Eligible = ≥ 20 POs. Bottom-3 by score whose OTD is below the
              eligible-vendor average <em>or</em> whose defect rate is above
              it. Vendors without an operational issue are skipped and the
              next lowest is picked instead.
            </p>
          </div>
          <div className="nb-vlist">
            {pip.length === 0
              ? <div className="nb-empty">
                  No PIP candidates — no eligible vendor has an OTD/defect
                  issue vs the benchmark.
                </div>
              : pip.map((v) => (
                  <VendorCard
                    key={v.vendor_id}
                    v={v}
                    tone="coral"
                    benchmark={benchmarks}
                    testId={ANALYTICS.pipCard(v.vendor_id)}
                  />
                ))}
          </div>
        </div>

        <div className="nb-panel" data-testid={ANALYTICS.rewardSection}>
          <div className="nb-panel__head">
            <Badge tone="teal">Recommended for continued / expanded business</Badge>
            <h2>Top 3 eligible vendors by composite score</h2>
            <p className="nb-panel__desc">
              Continued business subject to sole-source-risk and capacity
              checks done outside this analysis.
            </p>
          </div>
          <div className="nb-vlist">
            {reward.length === 0
              ? <div className="nb-empty">No eligible vendors ≥ 20 POs.</div>
              : reward.map((v) => (
                  <VendorCard
                    key={v.vendor_id}
                    v={v}
                    tone="teal"
                    testId={ANALYTICS.rewardCard(v.vendor_id)}
                  />
                ))}
          </div>
        </div>
      </section>

      {/* Charts row */}
      <section className="nb-charts">
        {monthly?.length > 0 && (
          <MonthlyTrendChart
            monthly={monthly}
            focusVendorId={focusVendor?.vendor_id}
            focusName={focusVendor?.vendor_name || "focus vendor"}
          />
        )}
        {delivery_buckets?.length > 0 && (pipIds.length + rewardIds.length) > 0 && (
          <DeliveryBucketsChart
            buckets={delivery_buckets}
            pipIds={pipIds}
            rewardIds={rewardIds}
            vendorsById={vendorsById}
          />
        )}
        {category?.length > 0 && <CategoryChart category={category} />}
      </section>

      {/* Decline story */}
      {declineTop && declineTop.delta_pct != null && declineTop.delta_pct > 0 && (
        <section className="nb-story">
          <div className="nb-story__eyebrow">The trend the average hides</div>
          <h2 className="nb-story__title">
            {declineTop.vendor_name}’s defect rate jumps{" "}
            <span className="nb-story__from">
              {pct(declineTop.pre_defect_pct, 2)}
            </span>{" "}
            →{" "}
            <span className="nb-story__to">
              {pct(declineTop.post_defect_pct, 2)}
            </span>{" "}
            after May
          </h2>
          <p className="nb-story__body">
            Comparing the pre-M4 window ({declineTop.n_pre} inspections) with
            the post-M4 window ({declineTop.n_post} inspections) surfaces a
            directional problem an annual average would have missed — which
            is exactly why the SQL analysis splits the timeline.
          </p>
        </section>
      )}

      {/* Leaderboard */}
      <section className="nb-leader">
        <div className="nb-leader__head">
          <div>
            <h2>Full vendor leaderboard</h2>
            <p className="nb-leader__desc">
              Composite = 0.40·OTD + 0.40·(100−Defect) + 0.20·(100−max(0,
              PriceVar%)). Eligibility ≥ 20 POs. Weights are academic, not
              industry-standard.
            </p>
          </div>
          <div className="nb-leader__filters">
            <label className="nb-picker">
              <span className="nb-picker__label">Region</span>
              <select
                value={filters.region}
                onChange={(e) => setFilters((f) => ({ ...f, region: e.target.value }))}
                data-testid={ANALYTICS.filterRegion}
              >
                {regions.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
            <label className="nb-picker">
              <span className="nb-picker__label">Category</span>
              <select
                value={filters.category}
                onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}
                data-testid={ANALYTICS.filterCategory}
              >
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
        </div>
        <div className="nb-table-wrap">
          <table className="nb-table" data-testid={ANALYTICS.leaderboardTable}>
            <thead>
              <tr>
                <th>#</th>
                <th>Vendor</th>
                <th>Region</th>
                <th>Category</th>
                <th className="ra">POs</th>
                <th className="ra">OTD %</th>
                <th className="ra">Defect %</th>
                <th className="ra">Fill %</th>
                <th className="ra">Price var %</th>
                <th className="ra">Lead d</th>
                <th className="ra">Score</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v, i) => {
                const isPip = pipIds.includes(v.vendor_id);
                const isRw  = rewardIds.includes(v.vendor_id);
                const flag  = isPip ? "PIP" : isRw ? "★" : "";
                return (
                  <tr
                    key={v.vendor_id}
                    data-testid={ANALYTICS.leaderboardRow(v.vendor_id)}
                    className={isPip ? "row-pip" : isRw ? "row-reward" : ""}
                  >
                    <td>{i + 1}</td>
                    <td>{v.vendor_name}</td>
                    <td>{v.region}</td>
                    <td>{v.vendor_category}</td>
                    <td className="ra">{v.total_pos}</td>
                    <td className="ra">{pct(v.otd_pct)}</td>
                    <td className="ra">{pct(v.defect_rate_pct, 2)}</td>
                    <td className="ra">{pct(v.fill_rate_pct)}</td>
                    <td className="ra">{pct(v.price_var_pct, 2)}</td>
                    <td className="ra">{num(v.avg_lead_days)}</td>
                    <td className="ra"><strong>{num(v.composite_score)}</strong></td>
                    <td>{flag && <Badge tone={isPip ? "coral" : "teal"}>{flag}</Badge>}</td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={12} className="nb-empty">No vendors match the current filters.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Data health panel */}
      <section className="nb-panel" data-testid={ANALYTICS.dataHealthPanel}>
        <div className="nb-panel__head">
          <Badge tone="ink">Data health</Badge>
          <h2>Cleaning decisions applied to this dataset</h2>
          <p className="nb-panel__desc">
            Every KPI on this page is computed on the cleaned frames. Numbers
            below match the cleaning notebook decisions one-to-one.
          </p>
        </div>
        <div className="nb-health__grid">
          {Object.entries(cleaning_log).map(([k, v]) => (
            <div key={k} className="nb-health__cell">
              <div className="nb-health__k">{k.replace(/_/g, " ")}</div>
              <div className="nb-health__v">{fmtInt(v)}</div>
            </div>
          ))}
          <div className="nb-health__cell">
            <div className="nb-health__k">inspection coverage</div>
            <div className="nb-health__v">{pct(totals.inspection_coverage_pct)}</div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="nb-footer">
        <div>
          <strong>Local analytics project</strong> — Python 3.11 · PostgreSQL ·
          Matplotlib · Power BI. This dashboard is a live demonstration of the
          methodology; the full reproducible repo (SQL + notebooks + report +
          DAX + PDF deck) lives at{" "}
          <code>/vendor-performance-analytics</code> in the codebase.
        </div>
        <div className="nb-footer__small">
          Data range {totals.earliest_order} → {totals.latest_order} &middot;{" "}
          <a href="/analytics/report.pdf" target="_blank" rel="noreferrer"
             data-testid={ANALYTICS.linkReport}>
            7-page PDF report
          </a>{" "}
          &middot;{" "}
          <a href="/analytics/deck.pdf" target="_blank" rel="noreferrer"
             data-testid={ANALYTICS.linkDeck}>
            5-slide deck
          </a>
        </div>
      </footer>
    </>
  );
}
