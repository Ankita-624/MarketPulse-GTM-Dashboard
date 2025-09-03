import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# --- Paths ---
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
CHARTS = OUT / "charts"

OUT.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

# --- Load data ---
sales = pd.read_csv(DATA / "marketpulse_sales.csv")
comps = pd.read_csv(DATA / "marketpulse_competitors.csv")
survey = pd.read_csv(DATA / "marketpulse_survey.csv")

sales["month_dt"] = pd.to_datetime(sales["month"] + "-01")
sales["revenue"] = sales["units_sold"] * sales["price"]

# --- Monthly KPIs ---
monthly = sales.groupby("month_dt").agg(
    leads=("leads","sum"),
    opportunities=("opportunities","sum"),
    deals_won=("deals_won","sum"),
    units_sold=("units_sold","sum"),
    revenue=("revenue","sum")
).reset_index()

monthly["opp_rate"] = (monthly["opportunities"] / monthly["leads"]).replace([np.inf, np.nan], 0.0)
monthly["win_rate"] = (monthly["deals_won"] / monthly["opportunities"]).replace([np.inf, np.nan], 0.0)
monthly["lead_to_win"] = (monthly["deals_won"] / monthly["leads"]).replace([np.inf, np.nan], 0.0)
monthly["rev_growth_pct"] = monthly["revenue"].pct_change().fillna(0.0)

# --- Region KPIs ---
region = sales.groupby("region").agg(
    leads=("leads","sum"),
    opportunities=("opportunities","sum"),
    deals_won=("deals_won","sum"),
    units_sold=("units_sold","sum"),
    revenue=("revenue","sum"),
    marketing_spend=("marketing_spend","sum")
).reset_index()
region["CAC"] = region["marketing_spend"] / region["deals_won"].replace(0, np.nan)
region["ACV"] = region["revenue"] / region["deals_won"].replace(0, np.nan)

# --- Product price vs win rate ---
opps_by_prod = sales.groupby("product")["opportunities"].sum()
wins_by_prod = sales.groupby("product")["deals_won"].sum()
avg_price_by_prod = sales.groupby("product")["price"].mean()
prod_win = pd.DataFrame({
    "product": avg_price_by_prod.index,
    "avg_price": avg_price_by_prod.values,
    "win_rate": (wins_by_prod / opps_by_prod).values
})

# --- Competitor summary ---
comp_summary = comps.groupby(["region","product"]).agg(
    avg_price_index=("price_index","mean"),
    avg_feature_rating=("feature_rating","mean"),
    avg_competitor_share=("market_share_estimate","mean")
).reset_index()

# --- Write Excel workbook ---
with pd.ExcelWriter(OUT / "marketpulse_summary.xlsx", engine="openpyxl") as w:
    sales.drop(columns=["month_dt"]).to_excel(w, sheet_name="raw_sales", index=False)
    comps.to_excel(w, sheet_name="competitors", index=False)
    survey.to_excel(w, sheet_name="survey", index=False)
    monthly.to_excel(w, sheet_name="kpi_by_month", index=False)
    region.to_excel(w, sheet_name="kpi_by_region", index=False)
    prod_win.to_excel(w, sheet_name="price_vs_win", index=False)
    comp_summary.to_excel(w, sheet_name="competitor_summary", index=False)

# --- CHARTS (one per figure, no custom colors) ---
# 1) Monthly revenue
plt.figure()
plt.plot(monthly["month_dt"], monthly["revenue"])
plt.title("Monthly Revenue")
plt.xlabel("Month"); plt.ylabel("Revenue")
plt.xticks(rotation=45)
plt.tight_layout(); plt.savefig(CHARTS / "monthly_revenue.png"); plt.close()

# 2) Region revenue (total)
reg_rev = region[["region","revenue"]].sort_values("revenue", ascending=False)
plt.figure()
plt.bar(reg_rev["region"], reg_rev["revenue"])
plt.title("Revenue by Region (Total)")
plt.xlabel("Region"); plt.ylabel("Revenue")
plt.tight_layout(); plt.savefig(CHARTS / "region_revenue.png"); plt.close()

# 3) Average conversion rates
labels = ["Lead→Opp", "Opp→Win", "Lead→Win"]
vals = [monthly["opp_rate"].mean(), monthly["win_rate"].mean(), monthly["lead_to_win"].mean()]
plt.figure()
plt.bar(labels, vals)
plt.title("Average Conversion Rates")
plt.xlabel("Stage"); plt.ylabel("Rate")
plt.tight_layout(); plt.savefig(CHARTS / "funnel_rates.png"); plt.close()

# 4) Avg price vs win rate (by product)
plt.figure()
plt.scatter(prod_win["avg_price"], prod_win["win_rate"])
for _, row in prod_win.iterrows():
    plt.annotate(row["product"], (row["avg_price"], row["win_rate"]))
plt.title("Avg Price vs Win Rate (by Product)")
plt.xlabel("Average Price"); plt.ylabel("Win Rate")
plt.tight_layout(); plt.savefig(CHARTS / "price_vs_win_rate.png"); plt.close()

# 5) Average competitor share
comp_share_mean = comps.groupby("competitor")["market_share_estimate"].mean().reset_index()
plt.figure()
plt.bar(comp_share_mean["competitor"], comp_share_mean["market_share_estimate"])
plt.title("Average Competitor Share")
plt.xlabel("Competitor"); plt.ylabel("Share")
plt.tight_layout(); plt.savefig(CHARTS / "competitor_share.png"); plt.close()

print("Done. Updated Excel and charts in:", OUT)
