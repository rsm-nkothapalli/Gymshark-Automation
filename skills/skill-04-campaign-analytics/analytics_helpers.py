"""
analytics_helpers.py — Skill 05: Campaign Performance Analytics
Gymshark GenAI Influencer Pipeline · Group 18

Data source: campaign_performance.csv (produced by data/simulate_campaigns.py)

Only trackable deal types are evaluated:
  - affiliate (UTM + promo code)
  - paid_creative_partnership (UTM link)
  - brand_ambassador (UTM + promo code)

Gift seeding is excluded — there is no reliable way to attribute revenue
to unpaid organic posts, so including it would distort ROI figures.
"""

TRACKABLE_DEALS = {"affiliate", "paid_creative_partnership", "brand_ambassador"}

import json
import os
import webbrowser

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas/matplotlib not installed. Run: uv add pandas matplotlib")


# ── Data loading ───────────────────────────────────────────────────────────────


def load_campaign_data(
    campaigns_path="data/campaign_performance.csv",
    partners_path="data/existing_partners.csv",
):
    """
    Load campaign_performance.csv, filter to trackable deal types only, and
    merge with existing_partners.csv. Gift seeding is excluded — organic posts
    have no UTM tracking so revenue attribution is not reliable.
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required. Run: uv add pandas")

    campaigns = pd.read_csv(campaigns_path)
    excluded = campaigns[~campaigns["deal_type"].isin(TRACKABLE_DEALS)]
    if not excluded.empty:
        print(f"Excluded {len(excluded)} gift_seeding row(s) — no trackable revenue.")
    campaigns = campaigns[campaigns["deal_type"].isin(TRACKABLE_DEALS)].copy()
    partners = pd.read_csv(partners_path)[["creator_id", "youtube_handle", "subscribers", "partner_since"]]
    return campaigns.merge(partners, on="creator_id", how="left")


REQUIRED_CAMPAIGN_COLS = [
    "campaign_id",
    "creator_id",
    "creator_name",
    "tier",
    "deal_type",
    "campaign_start",
    "campaign_end",
    "budget_gbp",
    "revenue_attributed_gbp",
    "promo_redemptions",
    "utm_clicks",
    "reach",
    "impressions",
]


def validate_campaign_columns(df):
    """Return list of missing required columns."""
    return [c for c in REQUIRED_CAMPAIGN_COLS if c not in df.columns]


# ── Metric calculations ────────────────────────────────────────────────────────


def calculate_campaign_metrics(df):
    """
    Add derived metric columns. Returns enriched DataFrame.
    Excludes zero-budget rows from ROI (gift seeding at no cost).
    """
    df = df.copy()
    budget = df["budget_gbp"].replace(0, float("nan"))
    clicks = df["utm_clicks"].replace(0, float("nan"))

    df["roi_pct"] = (df["revenue_attributed_gbp"] - df["budget_gbp"]) / budget * 100
    df["cost_per_click"] = df["budget_gbp"] / clicks
    df["conversion_rate_pct"] = df["promo_redemptions"] / clicks * 100
    df["revenue_per_pound"] = df["revenue_attributed_gbp"] / budget
    return df


def aggregate_by_tier(df):
    """Group by tier. Returns summary DataFrame sorted by avg ROI desc."""
    return (
        df.groupby("tier")
        .agg(
            campaigns=("campaign_id", "count"),
            avg_roi_pct=("roi_pct", "mean"),
            total_spend_gbp=("budget_gbp", "sum"),
            total_revenue_gbp=("revenue_attributed_gbp", "sum"),
            avg_conversion_pct=("conversion_rate_pct", "mean"),
        )
        .round(1)
        .reset_index()
        .sort_values("avg_roi_pct", ascending=False)
    )


def aggregate_by_deal_type(df):
    """Group by deal type. Returns summary DataFrame sorted by avg ROI desc."""
    return (
        df.groupby("deal_type")
        .agg(
            campaigns=("campaign_id", "count"),
            avg_roi_pct=("roi_pct", "mean"),
            avg_conversion_pct=("conversion_rate_pct", "mean"),
            total_revenue_gbp=("revenue_attributed_gbp", "sum"),
        )
        .round(1)
        .reset_index()
        .sort_values("avg_roi_pct", ascending=False)
    )


def get_top_performers(df, roi_threshold=150, conv_threshold=3):
    """Campaigns with ROI > roi_threshold AND conversion > conv_threshold."""
    mask = (df["roi_pct"] > roi_threshold) & (df["conversion_rate_pct"] > conv_threshold)
    cols = [
        "creator_name",
        "tier",
        "deal_type",
        "roi_pct",
        "conversion_rate_pct",
        "revenue_attributed_gbp",
        "renewal_recommended",
    ]
    return df[mask][cols].sort_values("roi_pct", ascending=False)


def get_bottom_performers(df, roi_threshold=20):
    """Campaigns with ROI below threshold or negative."""
    cols = ["creator_name", "tier", "deal_type", "roi_pct", "budget_gbp", "revenue_attributed_gbp"]
    return df[df["roi_pct"] < roi_threshold][cols].sort_values("roi_pct")


def portfolio_summary(df):
    """Return dict of top-level portfolio KPIs."""
    total_spend = df["budget_gbp"].sum()
    total_rev = df["revenue_attributed_gbp"].sum()
    blended_roi = ((total_rev - total_spend) / total_spend * 100) if total_spend else 0
    return {
        "campaigns_analysed": len(df),
        "total_spend_gbp": round(total_spend, 2),
        "total_revenue_gbp": round(total_rev, 2),
        "blended_roi_pct": round(blended_roi, 1),
    }


# ── Visualizations ─────────────────────────────────────────────────────────────

GYMSHARK_GREEN = "#00C896"
TIER_COLORS = {
    "nano": "#3498db",
    "micro": "#2ecc71",
    "mid": "#f39c12",
    "macro": "#e74c3c",
    "mega": "#9b59b6",
}


def generate_charts(metrics_df, output_dir="outputs/campaign_charts"):
    """
    Generate and save 3 charts to output_dir:
      1. Average ROI % by creator tier (bar)
      2. Campaign cost vs revenue attributed, coloured by tier (scatter + break-even line)
      3. Average ROI % by deal type (bar)
    Returns (path1, path2, path3).
    """
    if not HAS_PANDAS:
        raise ImportError("matplotlib is required. Run: uv add matplotlib")

    os.makedirs(output_dir, exist_ok=True)

    tier_summary = aggregate_by_tier(metrics_df)
    deal_summary = aggregate_by_deal_type(metrics_df)

    # ── Chart 1: ROI by tier ───────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [TIER_COLORS.get(t, "#aaa") for t in tier_summary["tier"]]
    bars = ax.bar(tier_summary["tier"], tier_summary["avg_roi_pct"], color=colors, width=0.5)
    ax.bar_label(bars, fmt="%.0f%%", padding=4, fontsize=9)
    ax.set_title("Average ROI by Creator Tier", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Tier", fontsize=10)
    ax.set_ylabel("Average ROI (%)", fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}%"))
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    path1 = os.path.join(output_dir, "roi_by_tier.png")
    fig.savefig(path1, dpi=150)
    plt.close()

    # ── Chart 2: Cost vs Revenue scatter ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    for tier, grp in metrics_df.groupby("tier"):
        ax.scatter(
            grp["budget_gbp"],
            grp["revenue_attributed_gbp"],
            label=tier.capitalize(),
            color=TIER_COLORS.get(tier, "#999"),
            alpha=0.8,
            s=70,
            edgecolors="white",
            linewidths=0.5,
        )
    max_val = max(metrics_df["budget_gbp"].max(), metrics_df["revenue_attributed_gbp"].max()) * 1.1
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.25, label="Break-even")
    ax.set_title("Campaign Cost vs Revenue Attributed", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Budget (£)", fontsize=10)
    ax.set_ylabel("Revenue Attributed (£)", fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x:,.0f}"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x:,.0f}"))
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    path2 = os.path.join(output_dir, "cost_vs_revenue.png")
    fig.savefig(path2, dpi=150)
    plt.close()

    # ── Chart 3: ROI by deal type ──────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(
        deal_summary["deal_type"],
        deal_summary["avg_roi_pct"],
        color=GYMSHARK_GREEN,
        width=0.5,
    )
    ax.bar_label(bars, fmt="%.0f%%", padding=4, fontsize=9)
    ax.set_title("Average ROI by Deal Type", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Deal Type", fontsize=10)
    ax.set_ylabel("Average ROI (%)", fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}%"))
    ax.tick_params(axis="x", rotation=15)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    path3 = os.path.join(output_dir, "roi_by_deal_type.png")
    fig.savefig(path3, dpi=150)
    plt.close()

    print(f"3 charts saved to {output_dir}/")
    return path1, path2, path3


def generate_tracked_revenue_chart(metrics_df, output_dir="outputs/campaign_charts"):
    """
    Horizontal bar chart: total revenue attributed per creator, filtered to
    affiliate and brand_ambassador only (deals with UTM/promo-code tracking).
    Bars coloured green (above average) vs grey (below average) so it's
    immediately clear who is driving sales and who isn't.
    Returns path to saved PNG.
    """
    if not HAS_PANDAS:
        raise ImportError("matplotlib is required. Run: uv add matplotlib")

    tracked = metrics_df[metrics_df["deal_type"].isin(["affiliate", "brand_ambassador"])].copy()

    if tracked.empty:
        print("No affiliate or brand_ambassador campaigns found.")
        return None

    # Sum revenue per creator across all their campaigns
    by_creator = (
        tracked.groupby(["creator_name", "deal_type"])
        .agg(
            total_revenue=("revenue_attributed_gbp", "sum"),
            campaigns=("campaign_id", "count"),
            avg_roi=("roi_pct", "mean"),
        )
        .reset_index()
        .sort_values("total_revenue", ascending=True)  # ascending for horizontal bars
    )

    avg_revenue = by_creator["total_revenue"].mean()

    # Colour: green if above average, grey if below
    colors = [GYMSHARK_GREEN if v >= avg_revenue else "#b0b0b0" for v in by_creator["total_revenue"]]

    fig, ax = plt.subplots(figsize=(10, 5))

    bars = ax.barh(
        by_creator["creator_name"],
        by_creator["total_revenue"],
        color=colors,
        height=0.55,
        edgecolor="white",
    )

    # Label each bar with £ value + deal type
    for bar, (_, row) in zip(bars, by_creator.iterrows()):
        label = f"  £{row['total_revenue']:,.0f}  ({row['deal_type'].replace('_', ' ')})"
        ax.text(
            bar.get_width() + by_creator["total_revenue"].max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=9,
        )

    # Average line
    ax.axvline(avg_revenue, color="#e74c3c", linestyle="--", linewidth=1.2, label=f"Average  £{avg_revenue:,.0f}")

    ax.set_title(
        "Revenue Attributed by Creator\n(Affiliate & Brand Ambassador — UTM-tracked only)",
        fontsize=13,
        fontweight="bold",
        pad=14,
    )
    ax.set_xlabel("Total Revenue Attributed (£)", fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x:,.0f}"))
    ax.legend(fontsize=9, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)

    # Extend x-axis so labels don't clip
    ax.set_xlim(0, by_creator["total_revenue"].max() * 1.45)

    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "tracked_revenue_by_creator.png")
    fig.savefig(path, dpi=150)
    plt.close()

    print(f"Tracked revenue chart saved to {path}")
    return path


def generate_html_dashboard(metrics_df, output_dir="outputs"):
    """
    Build a self-contained interactive HTML dashboard using Chart.js.
    Saves to outputs/campaign_dashboard.html and opens it in the browser.
    """
    os.makedirs(output_dir, exist_ok=True)

    summary = portfolio_summary(metrics_df)
    tier_agg = aggregate_by_tier(metrics_df)
    deal_agg = aggregate_by_deal_type(metrics_df)
    top = get_top_performers(metrics_df).reset_index(drop=True)
    bottom = get_bottom_performers(metrics_df).reset_index(drop=True)

    tracked = metrics_df[metrics_df["deal_type"].isin(["affiliate", "brand_ambassador"])].copy()
    if not tracked.empty:
        tracked_by_creator = (
            tracked.groupby(["creator_name", "deal_type"])
            .agg(total_revenue=("revenue_attributed_gbp", "sum"), avg_roi=("roi_pct", "mean"))
            .reset_index()
            .sort_values("total_revenue", ascending=True)
        )
        avg_tracked = float(tracked_by_creator["total_revenue"].mean())
    else:
        tracked_by_creator = pd.DataFrame(columns=["creator_name", "deal_type", "total_revenue", "avg_roi"])
        avg_tracked = 0.0

    def to_records(df):
        return json.loads(df.where(pd.notnull(df), None).to_json(orient="records"))

    scatter_datasets = []
    for tier, grp in metrics_df.groupby("tier"):
        scatter_datasets.append(
            {
                "label": tier.capitalize(),
                "data": [
                    {
                        "x": float(r["budget_gbp"]) if pd.notnull(r["budget_gbp"]) else None,
                        "y": float(r["revenue_attributed_gbp"]) if pd.notnull(r["revenue_attributed_gbp"]) else None,
                        "creator": r["creator_name"],
                    }
                    for _, r in grp.iterrows()
                ],
                "backgroundColor": TIER_COLORS.get(tier, "#999") + "bb",
                "borderColor": TIER_COLORS.get(tier, "#999"),
                "pointRadius": 8,
                "pointHoverRadius": 11,
            }
        )

    payload = json.dumps(
        {
            "summary": summary,
            "tier": to_records(tier_agg),
            "deal": to_records(deal_agg),
            "scatter": scatter_datasets,
            "tracked": to_records(tracked_by_creator),
            "avg_tracked": avg_tracked,
            "top": to_records(top),
            "bottom": to_records(bottom),
            "tier_colors": TIER_COLORS,
            "gs_green": GYMSHARK_GREEN,
        }
    )

    template = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gymshark · Campaign Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f4f5f9;color:#222}
header{background:#111;color:#fff;padding:22px 40px;display:flex;align-items:center;gap:16px}
header h1{font-size:20px;font-weight:700;letter-spacing:-.3px}
header h1 span{color:#00C896}
header p{font-size:12px;color:#777;margin-top:3px}
.badge{background:#00C896;color:#111;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.5px;margin-left:auto}
main{max-width:1300px;margin:0 auto;padding:28px 20px}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}
.kpi{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 4px rgba(0,0,0,.07);border-top:3px solid #00C896}
.kpi-label{font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:#999;margin-bottom:6px}
.kpi-value{font-size:26px;font-weight:700;color:#111}
.kpi-sub{font-size:11px;color:#aaa;margin-top:3px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}
.grid1{margin-bottom:18px}
.card{background:#fff;border-radius:10px;padding:22px;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.card h2{font-size:13px;font-weight:600;color:#555;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #f0f0f0}
.card h2 small{font-size:11px;color:#bbb;font-weight:400;display:block;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:7px 9px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:#aaa;border-bottom:2px solid #f0f0f0}
td{padding:8px 9px;border-bottom:1px solid #f7f7f7;color:#333}
tr:last-child td{border-bottom:none}
tr:hover td{background:#fafafa}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.green{background:#e6faf4;color:#00a87a}
.red{background:#fdecea;color:#c0392b}
.amber{background:#fef9e7;color:#c89000}
.empty{color:#ccc;text-align:center;padding:20px;font-size:13px}
.note{font-size:11px;color:#bbb;margin-top:8px}
</style>
</head>
<body>
<header>
  <div>
    <h1><span>Gymshark</span> · Campaign Performance Dashboard</h1>
    <p id="subtitle">Loading...</p>
  </div>
  <span class="badge">GROUP 18</span>
</header>
<main>
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-label">Campaigns Analysed</div><div class="kpi-value" id="k-campaigns">—</div><div class="kpi-sub">trackable deals only</div></div>
    <div class="kpi"><div class="kpi-label">Total Spend</div><div class="kpi-value" id="k-spend">—</div><div class="kpi-sub">affiliate + paid + ambassador</div></div>
    <div class="kpi"><div class="kpi-label">Revenue Attributed</div><div class="kpi-value" id="k-revenue">—</div><div class="kpi-sub">UTM-tracked</div></div>
    <div class="kpi" style="border-color:#f39c12"><div class="kpi-label">Blended ROI</div><div class="kpi-value" id="k-roi" style="color:#f39c12">—</div><div class="kpi-sub">all trackable campaigns</div></div>
  </div>
  <div class="grid2">
    <div class="card"><h2>Average ROI by Creator Tier</h2><canvas id="c-tier" height="230"></canvas></div>
    <div class="card"><h2>Average ROI by Deal Type</h2><canvas id="c-deal" height="230"></canvas></div>
  </div>
  <div class="grid1">
    <div class="card">
      <h2>Campaign Spend vs Revenue Attributed<small>Each dot = one campaign · hover for details</small></h2>
      <canvas id="c-scatter" height="160"></canvas>
    </div>
  </div>
  <div class="grid1">
    <div class="card">
      <h2>Revenue by Creator — Affiliate &amp; Brand Ambassador Only<small>Green = above average · Grey = below average · UTM-tracked deals only</small></h2>
      <canvas id="c-tracked" height="160"></canvas>
      <p class="note">* Paid creative excluded from this chart — promo code redemptions are tracked but not shown here separately</p>
    </div>
  </div>
  <div class="grid2">
    <div class="card"><h2>Top Performers<small>ROI &gt; 150% AND conversion &gt; 3%</small></h2><div id="t-top"></div></div>
    <div class="card"><h2>Bottom Performers<small>ROI &lt; 20% or negative</small></h2><div id="t-bottom"></div></div>
  </div>
</main>
<script>
const D = __DATA_JSON__;
const gbp = v => v==null?'N/A':'£'+Number(v).toLocaleString('en-GB',{maximumFractionDigits:0});
const pct = v => v==null?'N/A':Number(v).toFixed(1)+'%';
const cap = s => s?s.charAt(0).toUpperCase()+s.slice(1):s;

document.getElementById('k-campaigns').textContent = D.summary.campaigns_analysed;
document.getElementById('k-spend').textContent = gbp(D.summary.total_spend_gbp);
document.getElementById('k-revenue').textContent = gbp(D.summary.total_revenue_gbp);
document.getElementById('k-roi').textContent = pct(D.summary.blended_roi_pct);
document.getElementById('subtitle').textContent =
  D.summary.campaigns_analysed+' campaigns · Real Gymshark Partners · '+
  new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'});

Chart.defaults.font.family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";
Chart.defaults.font.size=12;
Chart.defaults.color='#666';

// ROI by tier
new Chart(document.getElementById('c-tier'),{
  type:'bar',
  data:{
    labels:D.tier.map(d=>cap(d.tier)),
    datasets:[{data:D.tier.map(d=>d.avg_roi_pct),backgroundColor:D.tier.map(d=>D.tier_colors[d.tier]||'#999'),borderRadius:6,borderSkipped:false}]
  },
  options:{
    plugins:{legend:{display:false},tooltip:{callbacks:{
      title:ctx=>cap(D.tier[ctx[0].dataIndex].tier)+' Tier',
      label:ctx=>[`Avg ROI: ${pct(ctx.parsed.y)}`,`Campaigns: ${D.tier[ctx[0].dataIndex].campaigns}`,`Total Revenue: ${gbp(D.tier[ctx[0].dataIndex].total_revenue_gbp)}`]
    }}},
    scales:{y:{ticks:{callback:v=>v+'%'},grid:{color:'#f5f5f5'}},x:{grid:{display:false}}}
  }
});

// ROI by deal type
new Chart(document.getElementById('c-deal'),{
  type:'bar',
  data:{
    labels:D.deal.map(d=>d.deal_type.replace(/_/g,' ')),
    datasets:[{data:D.deal.map(d=>d.avg_roi_pct),backgroundColor:D.gs_green,borderRadius:6,borderSkipped:false}]
  },
  options:{
    plugins:{legend:{display:false},tooltip:{callbacks:{
      title:ctx=>D.deal[ctx[0].dataIndex].deal_type.replace(/_/g,' '),
      label:ctx=>[`Avg ROI: ${pct(ctx.parsed.y)}`,`Campaigns: ${D.deal[ctx[0].dataIndex].campaigns}`,`Avg Conversion: ${pct(D.deal[ctx[0].dataIndex].avg_conversion_pct)}`]
    }}},
    scales:{y:{ticks:{callback:v=>v+'%'},grid:{color:'#f5f5f5'}},x:{grid:{display:false},ticks:{maxRotation:10}}}
  }
});

// Scatter
const allX=D.scatter.flatMap(s=>s.data.map(p=>p.x)).filter(v=>v!=null);
const allY=D.scatter.flatMap(s=>s.data.map(p=>p.y)).filter(v=>v!=null);
const maxV=Math.max(...allX,...allY)*1.1;
new Chart(document.getElementById('c-scatter'),{
  type:'scatter',
  data:{datasets:[...D.scatter,{label:'Break-even',data:[{x:0,y:0},{x:maxV,y:maxV}],type:'line',borderColor:'#ddd',borderDash:[5,4],borderWidth:1.5,pointRadius:0,fill:false}]},
  options:{
    plugins:{
      tooltip:{filter:i=>i.datasetIndex<D.scatter.length,callbacks:{label:ctx=>[ctx.raw.creator,`Spend: ${gbp(ctx.raw.x)}`,`Revenue: ${gbp(ctx.raw.y)}`]}},
      legend:{labels:{filter:i=>i.text!=='Break-even'||true}}
    },
    scales:{
      x:{title:{display:true,text:'Budget (£)'},ticks:{callback:v=>gbp(v)},grid:{color:'#f5f5f5'}},
      y:{title:{display:true,text:'Revenue Attributed (£)'},ticks:{callback:v=>gbp(v)},grid:{color:'#f5f5f5'}}
    }
  }
});

// Tracked revenue horizontal bar
if(D.tracked.length>0){
  const colors=D.tracked.map(d=>d.total_revenue>=D.avg_tracked?D.gs_green:'#d0d0d0');
  new Chart(document.getElementById('c-tracked'),{
    type:'bar',
    data:{
      labels:D.tracked.map(d=>d.creator_name),
      datasets:[{data:D.tracked.map(d=>d.total_revenue),backgroundColor:colors,borderRadius:5,borderSkipped:false}]
    },
    options:{
      indexAxis:'y',
      plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>{const d=D.tracked[ctx.dataIndex];return[`Revenue: ${gbp(d.total_revenue)}`,`Deal: ${d.deal_type.replace(/_/g,' ')}`,`Avg ROI: ${pct(d.avg_roi)}`];}}}},
      scales:{x:{ticks:{callback:v=>gbp(v)},grid:{color:'#f5f5f5'}},y:{grid:{display:false}}}
    }
  });
}else{
  document.getElementById('c-tracked').parentElement.innerHTML='<p class="empty">No affiliate or brand ambassador campaigns found.</p>';
}

// Tables
function table(id,rows,empty){
  const el=document.getElementById(id);
  if(!rows||!rows.length){el.innerHTML=`<p class="empty">${empty}</p>`;return;}
  const pill=roi=>roi>150?'green':roi<20?'red':'amber';
  el.innerHTML=`<table><thead><tr><th>Creator</th><th>Tier</th><th>Deal</th><th>ROI</th><th>Revenue</th></tr></thead><tbody>
    ${rows.map(r=>`<tr>
      <td>${r.creator_name}</td>
      <td>${cap(r.tier)}</td>
      <td style="font-size:11px;color:#999">${(r.deal_type||'').replace(/_/g,' ')}</td>
      <td><span class="pill ${pill(r.roi_pct)}">${pct(r.roi_pct)}</span></td>
      <td>${gbp(r.revenue_attributed_gbp)}</td>
    </tr>`).join('')}
  </tbody></table>`;
}
table('t-top',D.top,'No campaigns meet top performer criteria.');
table('t-bottom',D.bottom,'No underperforming campaigns — all looking good.');
</script>
</body>
</html>"""

    html = template.replace("__DATA_JSON__", payload)
    out_path = os.path.join(output_dir, "campaign_dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    abs_path = os.path.abspath(out_path)
    print(f"\nDashboard saved → {abs_path}")
    webbrowser.open(f"file://{abs_path}")
    return abs_path


# ── Run standalone ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_campaign_data()
    missing = validate_campaign_columns(df)
    if missing:
        print(f"Missing columns: {missing}")
    else:
        metrics = calculate_campaign_metrics(df)
        summary = portfolio_summary(metrics)
        print("\nPORTFOLIO SUMMARY")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        print("\nBY TIER:")
        print(aggregate_by_tier(metrics).to_string(index=False))
        print("\nBY DEAL TYPE:")
        print(aggregate_by_deal_type(metrics).to_string(index=False))
        generate_charts(metrics)
        generate_html_dashboard(metrics)
