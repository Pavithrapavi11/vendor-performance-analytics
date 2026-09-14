import { ANALYTICS } from "@/constants/testIds";
import { pct, num } from "@/api";

/* ============================================================================
 *  Reusable UI atoms used across the dashboard.
 * ========================================================================== */

export const Badge = ({ children, tone }) => (
  <span className={`nb-badge nb-badge--${tone}`}>{children}</span>
);

export const KpiCard = ({ label, value, tone = "ink", testId }) => (
  <div className={`nb-kpi nb-kpi--${tone}`} data-testid={testId}>
    <div className="nb-kpi__value">{value}</div>
    <div className="nb-kpi__label">{label}</div>
  </div>
);

export const VendorCard = ({ v, tone, testId, benchmark }) => (
  <div className={`nb-vcard nb-vcard--${tone}`} data-testid={testId}>
    <div className="nb-vcard__head">
      <div>
        <div className="nb-vcard__name">{v.vendor_name}</div>
        <div className="nb-vcard__meta">
          {v.vendor_id} &middot; {v.vendor_category} &middot; {v.total_pos} POs
        </div>
      </div>
      <div className="nb-vcard__score">
        <div className="nb-vcard__score-value">{num(v.composite_score)}</div>
        <div className="nb-vcard__score-label">score</div>
      </div>
    </div>
    <div className="nb-vcard__row">
      <div><div className="nb-vcard__k">OTD</div>       <div className="nb-vcard__v">{pct(v.otd_pct)}</div></div>
      <div><div className="nb-vcard__k">Defect</div>    <div className="nb-vcard__v">{pct(v.defect_rate_pct, 2)}</div></div>
      <div><div className="nb-vcard__k">Fill</div>      <div className="nb-vcard__v">{pct(v.fill_rate_pct)}</div></div>
      <div><div className="nb-vcard__k">Price var</div> <div className="nb-vcard__v">{pct(v.price_var_pct, 2)}</div></div>
    </div>
    {benchmark && (
      <div className="nb-vcard__note">
        Benchmark: OTD {pct(benchmark.avg_otd, 1)}, defect {pct(benchmark.avg_defect, 2)}
      </div>
    )}
  </div>
);
