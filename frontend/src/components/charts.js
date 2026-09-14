import {
  Line, LineChart, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
  BarChart, Bar,
} from "recharts";
import { ANALYTICS } from "@/constants/testIds";
import { pct } from "@/api";

const INK   = "#1D3557";
const TEAL  = "#0E7C86";
const CORAL = "#E76F51";
const SAND  = "#E9C46A";
const SLATE = "#4A5568";

const monthLabel = (iso) =>
  new Date(iso).toLocaleDateString("en-US", { month: "short", year: "2-digit" });

/* ------------------------------------------------------------------
 *  Monthly OTD % + Defect % trend for a chosen vendor overlaid on
 *  the "All vendors" average. Focus vendor defaults to the top PIP.
 * ------------------------------------------------------------------ */
export function MonthlyTrendChart({ monthly, focusVendorId, focusName }) {
  const overall = monthly
    .filter((r) => r.vendor_id === "__ALL__")
    .map((r) => ({ month: r.month, monthLabel: monthLabel(r.month),
                    otd_all: r.otd_pct, def_all: r.defect_rate_pct }));
  const focus = monthly
    .filter((r) => r.vendor_id === focusVendorId)
    .reduce((acc, r) => {
      acc[r.month] = { otd_focus: r.otd_pct, def_focus: r.defect_rate_pct };
      return acc;
    }, {});

  const data = overall.map((r) => ({ ...r, ...(focus[r.month] || {}) }));

  return (
    <div className="nb-chart" data-testid={ANALYTICS.chartMonthly}>
      <div className="nb-chart__head">
        <div className="nb-chart__title">Monthly trend</div>
        <div className="nb-chart__sub">
          OTD % (left) and defect % (right) — all vendors vs&nbsp;
          <strong>{focusName}</strong>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 12, right: 30, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E4DED0" />
          <XAxis dataKey="monthLabel" stroke={SLATE} fontSize={12} />
          <YAxis yAxisId="left"  stroke={SLATE} fontSize={12}
                 tickFormatter={(v) => `${Math.round(v)}%`} />
          <YAxis yAxisId="right" orientation="right" stroke={CORAL} fontSize={12}
                 tickFormatter={(v) => `${v.toFixed(1)}%`} />
          <Tooltip
            formatter={(value, key) =>
              value == null ? ["—", key] : [`${Number(value).toFixed(2)}%`, key]
            }
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine yAxisId="left" x="May 25" stroke={SLATE}
                         strokeDasharray="4 4" label={{ value: "M4",
                         position: "top", fill: SLATE, fontSize: 11 }} />
          <Line yAxisId="left"  type="monotone" dataKey="otd_all"    name="OTD % (all)"
                stroke={INK}   strokeWidth={2} dot={{ r: 3 }} connectNulls />
          <Line yAxisId="left"  type="monotone" dataKey="otd_focus"  name="OTD % (vendor)"
                stroke={TEAL}  strokeWidth={2} dot={{ r: 3 }} connectNulls />
          <Line yAxisId="right" type="monotone" dataKey="def_all"    name="Defect % (all)"
                stroke={SAND}  strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 3"
                connectNulls />
          <Line yAxisId="right" type="monotone" dataKey="def_focus"  name="Defect % (vendor)"
                stroke={CORAL} strokeWidth={2} dot={{ r: 3 }} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ------------------------------------------------------------------
 *  Stacked delivery-buckets bar for shortlisted vendors.
 * ------------------------------------------------------------------ */
export function DeliveryBucketsChart({ buckets, pipIds, rewardIds, vendorsById }) {
  const focusIds = [...pipIds, ...rewardIds];
  const data = buckets
    .filter((b) => focusIds.includes(b.vendor_id))
    .map((b) => ({
      vendor_name: vendorsById[b.vendor_id]?.vendor_name || b.vendor_id,
      "On time":            b["On Time"],
      "Slightly late":      b["Slightly Late"],
      "Significantly late": b["Significantly Late"],
      isPip: pipIds.includes(b.vendor_id),
    }))
    .sort((a, b) => (a.isPip === b.isPip ? 0 : a.isPip ? -1 : 1));

  return (
    <div className="nb-chart" data-testid={ANALYTICS.chartBuckets}>
      <div className="nb-chart__head">
        <div className="nb-chart__title">Delivery buckets</div>
        <div className="nb-chart__sub">
          PIP + reward vendors, POs grouped by lateness
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 12, right: 20, left: 8, bottom: 40 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E4DED0" />
          <XAxis dataKey="vendor_name" stroke={SLATE} fontSize={11}
                 angle={-18} textAnchor="end" interval={0} height={60} />
          <YAxis stroke={SLATE} fontSize={12} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="On time"            stackId="a" fill={TEAL}  />
          <Bar dataKey="Slightly late"      stackId="a" fill={SAND}  />
          <Bar dataKey="Significantly late" stackId="a" fill={CORAL} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ------------------------------------------------------------------
 *  Category KPI grouped bar (OTD % and defect % per category).
 * ------------------------------------------------------------------ */
export function CategoryChart({ category }) {
  const data = category.map((c) => ({
    category: c.vendor_category,
    "OTD %":    c.otd_pct,
    "Defect %": c.defect_rate_pct,
  }));
  return (
    <div className="nb-chart" data-testid={ANALYTICS.chartCategory}>
      <div className="nb-chart__head">
        <div className="nb-chart__title">Category performance</div>
        <div className="nb-chart__sub">OTD % vs defect % across categories</div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 12, right: 20, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E4DED0" />
          <XAxis dataKey="category" stroke={SLATE} fontSize={12} />
          <YAxis yAxisId="left"  stroke={INK}   fontSize={12}
                 tickFormatter={(v) => `${Math.round(v)}%`} />
          <YAxis yAxisId="right" orientation="right" stroke={CORAL} fontSize={12}
                 tickFormatter={(v) => `${v.toFixed(1)}%`} />
          <Tooltip formatter={(v) => (v == null ? "—" : `${Number(v).toFixed(2)}%`)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar yAxisId="left"  dataKey="OTD %"    fill={INK}   radius={[6, 6, 0, 0]} />
          <Bar yAxisId="right" dataKey="Defect %" fill={CORAL} radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
