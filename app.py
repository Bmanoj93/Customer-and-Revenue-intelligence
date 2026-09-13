# """
# Customer & Revenue Intelligence Platform
# -----------------------------------------
# A Streamlit dashboard that reads Gold-layer tables from a Databricks SQL
# Warehouse (catalog: adventure_works_cata, schema: default) and mirrors the
# Power BI report, plus an AI Business Insights page powered by the Anthropic
# Claude API.

# Run with:  streamlit run app.py
# """
# """
# Customer & Revenue Intelligence Platform
# -----------------------------------------
# A Streamlit dashboard that reads Gold-layer tables from a Databricks SQL
# Warehouse (catalog: adventure_works_cata, schema: default) and mirrors the
# Power BI report, plus an AI Business Insights page powered by the Anthropic
# Claude API.

# Run with:  streamlit run app.py
# """

# import time
# import textwrap
# from datetime import datetime

# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# import streamlit as st
# from databricks import sql as databricks_sql

# # ==========================================================================
# # 0. CONFIG — CATALOG / SCHEMA / COLUMN NAMES
# # --------------------------------------------------------------------------
# # If a column in YOUR gold table is named differently than assumed below,
# # change it ONLY here — the rest of the app uses these constants, so you
# # never have to go hunting through the whole file.
# # ==========================================================================

# CATALOG = "workspace"   # fixed: your gold tables live in the workspace catalog, not adventure_works_cata
# SCHEMA = "default"

# TABLES = {
#     "gold_kpi": f"{CATALOG}.{SCHEMA}.gold_kpi",
#     "gold_monthly_revenue": f"{CATALOG}.{SCHEMA}.gold_monthly_revenue",
#     "gold_customer_summary": f"{CATALOG}.{SCHEMA}.gold_customer_summary",
#     "gold_product_summary": f"{CATALOG}.{SCHEMA}.gold_product_summary",
#     "gold_category_summary": f"{CATALOG}.{SCHEMA}.gold_category_summary",
#     "gold_territory_summary": f"{CATALOG}.{SCHEMA}.gold_territory_summary",
#     "gold_return_summary": f"{CATALOG}.{SCHEMA}.gold_return_summary",
#     "gold_customer_churn": f"{CATALOG}.{SCHEMA}.gold_customer_churn",
# }

# # Column name assumptions (edit the right-hand side if yours differ)
# COL = {
#     # gold_kpi (usually one row with overall totals)
#     "kpi_revenue": "TotalRevenue",
#     "kpi_profit": "TotalProfit",
#     "kpi_orders": "TotalOrders",
#     "kpi_customers": "TotalCustomers",
#     "kpi_quantity": "TotalQuantity",
#     # gold_monthly_revenue
#     "year": "Year",
#     "month": "Month",
#     "month_revenue": "Revenue",
#     "month_profit": "Profit",
#     # gold_category_summary
#     "category": "CategoryName",
#     "category_revenue": "TotalRevenue",
#     "category_profit": "TotalProfit",
#     # gold_territory_summary
#     "territory": "Region",
#     "territory_revenue": "TotalRevenue",
#     "territory_profit": "TotalProfit",
#     "territory_orders": "TotalOrders",
#     # gold_customer_summary
#     "customer_name": "CustomerKey",  # no name column in gold_customer_summary — showing the numeric ID instead
#     "customer_revenue": "TotalRevenue",
#     "customer_orders": "TotalOrders",
#     # gold_product_summary
#     "product_name": "ProductKey",  # no name column in gold_product_summary — showing the numeric ID instead
#     "product_revenue": "TotalRevenue",
#     "product_profit": "TotalProfit",
#     "product_qty": "UnitsSold",
#     # gold_return_summary
#     "return_product": "ProductName",
#     "return_category": "CategoryName",
#     "return_qty": "TotalReturnedQuantity",
#     "return_rate": "ReturnRate",
#     # gold_customer_churn
#     "churn_customer": "CustomerKey",  # no name column in gold_customer_churn — showing the numeric ID instead
#     "churn_status": "ChurnStatus",       # expected values like "Churned" / "Active"
#     "churn_recency": "RecencyDays",
#     "churn_revenue": "TotalRevenue",
# }

# REFRESH_TTL_SECONDS = 600  # how long query results are cached before re-reading Databricks

# # ==========================================================================
# # 1. PAGE CONFIG & STYLING
# # ==========================================================================

# st.set_page_config(
#     page_title="Customer & Revenue Intelligence Platform",
#     page_icon="📊",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # ---- Brand palette (edit these lines to re-theme the whole app) ----
# ACCENT = "#14B8A6"        # primary accent (teal)
# BG_DARK = "#0B1220"       # app background
# CARD_DARK = "#141B2E"     # floating card surface
# BORDER_DARK = "rgba(255,255,255,0.08)"
# TEXT_LIGHT = "#E5E7EB"
# TEXT_MUTED = "#94A3B8"
# NAVY = "#0F1729"          # sidebar surface (close to BG_DARK for a seamless look)
# CTA_GRADIENT = "linear-gradient(135deg, #FF7676 0%, #FF9A5A 100%)"  # coral CTA pill

# CHART_COLORWAY = ["#22D3EE", "#14B8A6", "#F472B6", "#F59E0B", "#818CF8", "#84CC16"]

# st.markdown(
#     textwrap.dedent(
#         """
#     <link rel="preconnect" href="https://fonts.googleapis.com">
#     <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
#     <style>
#     html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

#     /* ---- App background with two soft neon glows, like the reference ---- */
#     [data-testid="stAppViewContainer"] > .main {
#         background:
#             radial-gradient(circle at 0%% 15%%, rgba(34,211,238,0.10), transparent 35%%),
#             radial-gradient(circle at 100%% 15%%, rgba(244,114,182,0.10), transparent 35%%),
#             %(bg_dark)s;
#     }
#     [data-testid="stHeader"] { background: transparent; }

#     /* ---- Top page header ---- */
#     .page-header { margin-bottom: 6px; }
#     .page-header h1 { font-size: 1.55rem; font-weight: 700; color: %(text_light)s; margin: 0; line-height: 1.2; }
#     .page-header p { font-size: 0.9rem; color: %(text_muted)s; margin: 2px 0 0 0; }
#     .page-divider { border: none; border-top: 1px solid %(border_dark)s; margin: 14px 0 20px 0; }

#     /* ---- KPI cards ---- */
#     .kpi-card {
#         position: relative;
#         background: %(card_dark)s;
#         border: 1px solid %(border_dark)s;
#         border-radius: 14px;
#         padding: 16px 18px 16px 18px;
#         box-shadow: 0 4px 18px rgba(0,0,0,0.25);
#         transition: box-shadow 0.15s ease, transform 0.15s ease;
#         overflow: hidden;
#     }
#     .kpi-card:hover { box-shadow: 0 8px 26px rgba(0,0,0,0.35); transform: translateY(-1px); }
#     .kpi-card::before {
#         content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
#         background: var(--kpi-accent, %(accent)s);
#     }
#     .kpi-top { display: flex; align-items: center; justify-content: space-between; }
#     .kpi-icon {
#         width: 30px; height: 30px; border-radius: 8px;
#         display: flex; align-items: center; justify-content: center;
#         font-size: 15px; background: rgba(255,255,255,0.06); color: var(--kpi-accent, %(accent)s);
#     }
#     .kpi-label {
#         font-size: 0.72rem; color: %(text_muted)s; font-weight: 600;
#         text-transform: uppercase; letter-spacing: 0.04em; margin-top: 10px;
#     }
#     .kpi-value {
#         font-size: 1.55rem; font-weight: 700; color: %(text_light)s;
#         margin-top: 2px; letter-spacing: -0.01em;
#     }

#     /* ---- Alerts ---- */
#     .alert-high {background:rgba(220,38,38,0.14); border-left:4px solid #f87171; padding:12px 14px; border-radius:8px; margin-bottom:8px; color:#fecaca;}
#     .alert-medium {background:rgba(217,119,6,0.14); border-left:4px solid #fbbf24; padding:12px 14px; border-radius:8px; margin-bottom:8px; color:#fde68a;}
#     .alert-low {background:rgba(37,99,235,0.14); border-left:4px solid #60a5fa; padding:12px 14px; border-radius:8px; margin-bottom:8px; color:#bfdbfe;}

#     /* ---- Section labels above charts ---- */
#     .section-label { font-size: 0.95rem; font-weight: 600; color: %(text_light)s; margin-bottom: 2px; }

#     /* ---- Chart / table panels ---- */
#     div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"], div[data-testid="stExpander"] {
#         background: %(card_dark)s; border: 1px solid %(border_dark)s; border-radius: 14px; padding: 6px;
#     }

#     /* ---- Sidebar ---- */
#     section[data-testid="stSidebar"] {background-color: %(navy)s; border-right: 1px solid %(border_dark)s;}
#     section[data-testid="stSidebar"] * {color: %(text_light)s !important;}
#     section[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,0.08);}
#     .sidebar-brand { padding: 4px 0 16px 0; }
#     .sidebar-brand .name { font-size: 0.95rem; font-weight: 700; line-height: 1.15; }
#     .sidebar-brand .tagline { font-size: 0.72rem; color: %(text_muted)s !important; }
#     div[data-testid="stSidebar"] div[role="radiogroup"] label {
#         padding: 8px 12px; border-radius: 10px; margin-bottom: 2px; transition: background 0.15s ease;
#     }
#     div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
#         background: #ffffff !important;
#     }
#     div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
#         color: %(bg_dark)s !important; font-weight: 600;
#     }
#     .sidebar-profile {
#         display: flex; align-items: center; gap: 10px;
#         background: rgba(255,255,255,0.05); border: 1px solid %(border_dark)s;
#         border-radius: 12px; padding: 10px 12px; margin-top: 10px;
#     }
#     .sidebar-profile .dot {
#         width: 8px; height: 8px; border-radius: 50%%; background: #4ade80; flex-shrink: 0;
#         box-shadow: 0 0 0 3px rgba(74,222,128,0.18);
#     }
#     .sidebar-profile .who { font-size: 0.78rem; font-weight: 600; line-height: 1.2; }
#     .sidebar-profile .role { font-size: 0.68rem; color: %(text_muted)s !important; }

#     /* ---- Buttons ---- */
#     .stButton > button {
#         border-radius: 8px; font-weight: 600; border: 1px solid %(border_dark)s;
#         background: %(card_dark)s; color: %(text_light)s;
#     }
#     .stButton > button[kind="primary"] {
#         background: %(cta_gradient)s; border: none; color: #ffffff;
#         border-radius: 999px; box-shadow: 0 6px 16px rgba(255, 118, 118, 0.35);
#     }
#     .stButton > button[kind="primary"]:hover { opacity: 0.92; color: #ffffff; }
#     section[data-testid="stSidebar"] .stButton > button {
#         background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
#         border-radius: 8px;
#     }

#     /* ---- Login screen ---- */
#     div[data-testid="stVerticalBlockBorderWrapper"] {
#         border-radius: 20px !important; box-shadow: 0 20px 60px rgba(0,0,0,0.4);
#     }
#     .login-title { text-align: center; font-size: 1.25rem; font-weight: 700; color: #111827; margin-bottom: 2px; margin-top: 4px; }
#     .login-sub { text-align: center; font-size: 0.85rem; color: #6b7280; margin-bottom: 20px; }
#     </style>
#     """
#     )
#     % {
#         "accent": ACCENT,
#         "bg_dark": BG_DARK,
#         "card_dark": CARD_DARK,
#         "border_dark": BORDER_DARK,
#         "text_light": TEXT_LIGHT,
#         "text_muted": TEXT_MUTED,
#         "navy": NAVY,
#         "cta_gradient": CTA_GRADIENT,
#     },
#     unsafe_allow_html=True,
# )

# px.defaults.template = "plotly_dark"
# px.defaults.color_discrete_sequence = CHART_COLORWAY


# def style_fig(fig):
#     """Apply a consistent, minimal dark look to every Plotly figure in the app."""
#     fig.update_layout(
#         margin=dict(l=10, r=10, t=10, b=10),
#         font=dict(family="Inter, sans-serif", size=12, color=TEXT_MUTED),
#         plot_bgcolor="rgba(0,0,0,0)",
#         paper_bgcolor="rgba(0,0,0,0)",
#         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
#         hoverlabel=dict(bgcolor=CARD_DARK, font_size=12, font_color=TEXT_LIGHT),
#     )
#     fig.update_xaxes(showgrid=False, showline=True, linecolor="rgba(255,255,255,0.15)")
#     fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False)
#     return fig


# def page_header(icon: str, title: str, subtitle: str = ""):
#     st.markdown(
#         textwrap.dedent(
#             f"""
#         <div class="page-header">
#             <div>
#                 <h1>{title}</h1>
#                 {f'<p>{subtitle}</p>' if subtitle else ''}
#             </div>
#         </div>
#         <hr class="page-divider" />
#         """
#         ),
#         unsafe_allow_html=True,
#     )

# # ==========================================================================
# # 2. DATABRICKS CONNECTION
# # ==========================================================================


# def get_secret(key: str, default=None, required: bool = False):
#     """Read one value from st.secrets with a friendly error instead of a raw
#     traceback when secrets.toml is missing or the key isn't set."""
#     try:
#         if key in st.secrets:
#             return st.secrets[key]
#     except Exception:
#         pass
#     if required:
#         st.error(
#             f"Missing secret **`{key}`**.\n\n"
#             "Make sure `.streamlit/secrets.toml` exists in your project folder "
#             "(copy it from `.streamlit/secrets.toml.example` and rename the copy to "
#             "`secrets.toml`), then fill in the required values and restart the app."
#         )
#         st.stop()
#     return default


# @st.cache_resource(show_spinner=False)
# def get_connection():
#     """Open (and cache) one Databricks SQL Warehouse connection for the app."""
#     return databricks_sql.connect(
#         server_hostname=get_secret("DATABRICKS_SERVER_HOSTNAME", required=True),
#         http_path=get_secret("DATABRICKS_HTTP_PATH", required=True),
#         access_token=get_secret("DATABRICKS_TOKEN", required=True),
#     )


# @st.cache_data(ttl=REFRESH_TTL_SECONDS, show_spinner="Reading data from Databricks…")
# def run_query(query: str) -> pd.DataFrame:
#     """Run a SQL query against Databricks and return a DataFrame."""
#     conn = get_connection()
#     with conn.cursor() as cursor:
#         cursor.execute(query)
#         columns = [desc[0] for desc in cursor.description]
#         rows = cursor.fetchall()
#     return pd.DataFrame(rows, columns=columns)


# def load_table(table_key: str) -> pd.DataFrame:
#     """Load an entire gold table by its key in TABLES."""
#     full_name = TABLES[table_key]
#     try:
#         return run_query(f"SELECT * FROM {full_name}")
#     except Exception as e:
#         st.error(
#             f"Could not read `{full_name}` from Databricks.\n\n"
#             f"Details: {e}"
#         )
#         return pd.DataFrame()


# def col(df: pd.DataFrame, key: str):
#     """Safely fetch a configured column from a dataframe, or None if missing."""
#     name = COL.get(key)
#     if name and name in df.columns:
#         return df[name]
#     return None


# def safe_sum(df: pd.DataFrame, key: str) -> float:
#     series = col(df, key)
#     return float(series.sum()) if series is not None else 0.0


# def safe_first(df: pd.DataFrame, key: str, default=0):
#     series = col(df, key)
#     if series is not None and len(series) > 0:
#         return series.iloc[0]
#     return default


# def sorted_monthly(df: pd.DataFrame) -> pd.DataFrame:
#     """Sort gold_monthly_revenue chronologically and add a 'Period' label
#     (e.g. '2024-03') so multi-year data doesn't get jumbled by month number alone."""
#     if df.empty:
#         return df
#     df = df.copy()
#     if COL["year"] in df.columns and COL["month"] in df.columns:
#         df = df.sort_values([COL["year"], COL["month"]])
#         df["Period"] = df[COL["year"]].astype(str) + "-" + df[COL["month"]].astype(str).str.zfill(2)
#     elif COL["month"] in df.columns:
#         df = df.sort_values(COL["month"])
#         df["Period"] = df[COL["month"]]
#     return df


# # ==========================================================================
# # 3. UI HELPERS
# # ==========================================================================


# def kpi_card(label: str, value: str, icon: str = "📊", accent: str = None, accent_soft: str = None):
#     style_vars = ""
#     if accent:
#         style_vars += f"--kpi-accent:{accent};"
#     if accent_soft:
#         style_vars += f"--kpi-accent-soft:{accent_soft};"
#     st.markdown(
#         textwrap.dedent(
#             f"""
#         <div class="kpi-card" style="{style_vars}">
#             <div class="kpi-top">
#                 <div class="kpi-icon">{icon}</div>
#             </div>
#             <div class="kpi-label">{label}</div>
#             <div class="kpi-value">{value}</div>
#         </div>
#         """
#         ),
#         unsafe_allow_html=True,
#     )


# def section_label(text: str):
#     st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


# def fmt_currency(x: float) -> str:
#     try:
#         return f"${x:,.0f}"
#     except Exception:
#         return str(x)


# def fmt_number(x: float) -> str:
#     try:
#         return f"{x:,.0f}"
#     except Exception:
#         return str(x)


# def fmt_percent(x: float) -> str:
#     try:
#         return f"{x:.1f}%"
#     except Exception:
#         return str(x)


# def render_alerts(alerts: list):
#     if not alerts:
#         st.success("No alerts — all monitored metrics look healthy.")
#         return
#     priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
#     for a in sorted(alerts, key=lambda x: priority_order.get(x["priority"], 3)):
#         css_class = f"alert-{a['priority'].lower()}"
#         st.markdown(
#             textwrap.dedent(
#                 f"""
#             <div class="{css_class}">
#                 <b>{a['priority']} — {a['title']}</b><br/>
#                 {a['detail']}
#             </div>
#             """
#             ),
#             unsafe_allow_html=True,
#         )


# # ==========================================================================
# # 4. ALERT LOGIC (rule-based, computed locally — separate from Claude)
# # ==========================================================================


# def compute_alerts(metrics: dict) -> list:
#     alerts = []

#     churn_rate = metrics.get("churn_rate")
#     if churn_rate is not None and churn_rate >= 25:
#         alerts.append({
#             "priority": "HIGH",
#             "title": "High churn rate",
#             "detail": f"Churn rate is {churn_rate:.1f}%, which is high. Investigate at-risk segments.",
#         })
#     elif churn_rate is not None and churn_rate >= 15:
#         alerts.append({
#             "priority": "MEDIUM",
#             "title": "Elevated churn rate",
#             "detail": f"Churn rate is {churn_rate:.1f}%. Worth monitoring closely.",
#         })

#     rev_trend = metrics.get("revenue_trend_pct")
#     if rev_trend is not None and rev_trend <= -10:
#         alerts.append({
#             "priority": "HIGH",
#             "title": "Revenue decline",
#             "detail": f"Revenue is down {abs(rev_trend):.1f}% versus the prior period.",
#         })
#     elif rev_trend is not None and rev_trend <= -3:
#         alerts.append({
#             "priority": "MEDIUM",
#             "title": "Revenue softening",
#             "detail": f"Revenue is down {abs(rev_trend):.1f}% versus the prior period.",
#         })

#     profit_trend = metrics.get("profit_trend_pct")
#     if profit_trend is not None and profit_trend <= -10:
#         alerts.append({
#             "priority": "HIGH",
#             "title": "Profit decline",
#             "detail": f"Profit is down {abs(profit_trend):.1f}% versus the prior period.",
#         })

#     return_rate = metrics.get("avg_return_rate")
#     if return_rate is not None and return_rate >= 10:
#         alerts.append({
#             "priority": "HIGH",
#             "title": "High product returns",
#             "detail": f"Average return rate is {return_rate:.1f}%, above the 10% threshold.",
#         })
#     elif return_rate is not None and return_rate >= 5:
#         alerts.append({
#             "priority": "MEDIUM",
#             "title": "Rising returns",
#             "detail": f"Average return rate is {return_rate:.1f}%.",
#         })

#     worst_territory = metrics.get("worst_territory")
#     if worst_territory:
#         alerts.append({
#             "priority": "LOW",
#             "title": "Underperforming territory",
#             "detail": f"{worst_territory} is the lowest-revenue territory this period.",
#         })

#     high_recency = metrics.get("high_recency_customers")
#     if high_recency:
#         alerts.append({
#             "priority": "MEDIUM",
#             "title": "Significant customer inactivity",
#             "detail": f"{high_recency} customers have not purchased recently (high RecencyDays).",
#         })

#     return alerts


# # ==========================================================================
# # 5. PAGES
# # ==========================================================================


# def page_executive_overview():
#     page_header("📈", "Executive overview", "Company-wide revenue, profit and demand at a glance")

#     kpi_df = load_table("gold_kpi")
#     monthly_df = load_table("gold_monthly_revenue")
#     category_df = load_table("gold_category_summary")
#     territory_df = load_table("gold_territory_summary")

#     alerts = compute_alerts(gather_aggregated_metrics())
#     if alerts:
#         section_label(f"⚠️ Alerts ({len(alerts)})")
#         render_alerts(alerts)
#         st.write("")

#     total_revenue = safe_first(kpi_df, "kpi_revenue") if not kpi_df.empty else safe_sum(monthly_df, "month_revenue")
#     total_profit = safe_first(kpi_df, "kpi_profit") if not kpi_df.empty else safe_sum(monthly_df, "month_profit")
#     total_orders = safe_first(kpi_df, "kpi_orders")
#     total_customers = safe_first(kpi_df, "kpi_customers")
#     total_quantity = safe_first(kpi_df, "kpi_quantity")

#     c1, c2, c3, c4, c5 = st.columns(5)
#     with c1:
#         kpi_card("Total Revenue", fmt_currency(total_revenue), icon="💰", accent="#4F46E5", accent_soft="#EEF2FF")
#     with c2:
#         kpi_card("Total Profit", fmt_currency(total_profit), icon="📈", accent="#0EA5A6", accent_soft="#ECFEFF")
#     with c3:
#         kpi_card("Total Orders", fmt_number(total_orders), icon="🧾", accent="#F59E0B", accent_soft="#FFFBEB")
#     with c4:
#         kpi_card("Total Customers", fmt_number(total_customers), icon="👥", accent="#0284C7", accent_soft="#F0F9FF")
#     with c5:
#         kpi_card("Total Quantity", fmt_number(total_quantity), icon="📦", accent="#84CC16", accent_soft="#F7FEE7")

#     st.write("")

#     col1, col2 = st.columns(2)
#     with col1:
#         section_label("Revenue trend")
#         if not monthly_df.empty and COL["month"] in monthly_df.columns:
#             m = sorted_monthly(monthly_df)
#             fig = px.line(m, x="Period", y=COL["month_revenue"], markers=True)
#             fig.update_traces(line_color=CHART_COLORWAY[0], marker=dict(size=6))
#             st.plotly_chart(style_fig(fig), use_container_width=True)
#         else:
#             st.info("No data available in gold_monthly_revenue.")

#     with col2:
#         section_label("Profit trend")
#         if not monthly_df.empty and COL["month"] in monthly_df.columns and COL["month_profit"] in monthly_df.columns:
#             m = sorted_monthly(monthly_df)
#             fig = px.line(m, x="Period", y=COL["month_profit"], markers=True)
#             fig.update_traces(line_color=CHART_COLORWAY[1], marker=dict(size=6))
#             st.plotly_chart(style_fig(fig), use_container_width=True)
#         else:
#             st.info("No profit trend data available.")

#     col3, col4 = st.columns(2)
#     with col3:
#         section_label("Revenue by category")
#         if not category_df.empty:
#             fig = px.bar(
#                 category_df.sort_values(COL["category_revenue"], ascending=False),
#                 x=COL["category"], y=COL["category_revenue"],
#             )
#             fig.update_traces(marker_color=CHART_COLORWAY[0])
#             st.plotly_chart(style_fig(fig), use_container_width=True)
#         else:
#             st.info("No data available in gold_category_summary.")

#     with col4:
#         section_label("Revenue by territory")
#         if not territory_df.empty:
#             fig = px.bar(
#                 territory_df.sort_values(COL["territory_revenue"], ascending=False),
#                 x=COL["territory"], y=COL["territory_revenue"], color=COL["territory"],
#             )
#             fig.update_layout(showlegend=False)
#             st.plotly_chart(style_fig(fig), use_container_width=True)
#         else:
#             st.info("No data available in gold_territory_summary.")


# def page_customer_intelligence():
#     page_header("👥", "Customer intelligence", "Who your customers are and where revenue concentrates")
#     df = load_table("gold_customer_summary")

#     if df.empty:
#         st.warning("gold_customer_summary returned no rows.")
#         return

#     customer_count = len(df)
#     total_customer_revenue = safe_sum(df, "customer_revenue")

#     c1, c2 = st.columns(2)
#     with c1:
#         kpi_card("Customer Count", fmt_number(customer_count), icon="👥", accent="#0284C7", accent_soft="#F0F9FF")
#     with c2:
#         kpi_card("Total Customer Revenue", fmt_currency(total_customer_revenue), icon="💰", accent="#4F46E5", accent_soft="#EEF2FF")

#     st.write("")

#     top10 = df.sort_values(COL["customer_revenue"], ascending=False).head(10)

#     col1, col2 = st.columns([1, 1])
#     with col1:
#         section_label("Top 10 customers by revenue")
#         fig = px.bar(
#             top10.sort_values(COL["customer_revenue"]),
#             x=COL["customer_revenue"], y=COL["customer_name"], orientation="h",
#         )
#         fig.update_traces(marker_color=CHART_COLORWAY[0])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     with col2:
#         section_label("Customer revenue distribution")
#         fig = px.histogram(df, x=COL["customer_revenue"], nbins=30)
#         fig.update_traces(marker_color=CHART_COLORWAY[3])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     with st.expander("Top customers — detail table"):
#         st.dataframe(top10, use_container_width=True)


# def page_product_intelligence():
#     page_header("📦", "Product intelligence", "Best sellers by revenue, profit and volume")
#     df = load_table("gold_product_summary")

#     if df.empty:
#         st.warning("gold_product_summary returned no rows.")
#         return

#     top_revenue = df.sort_values(COL["product_revenue"], ascending=False).head(10)
#     top_profit = df.sort_values(COL["product_profit"], ascending=False).head(10) if COL["product_profit"] in df.columns else pd.DataFrame()

#     col1, col2 = st.columns(2)
#     with col1:
#         section_label("Top products by revenue")
#         fig = px.bar(top_revenue.sort_values(COL["product_revenue"]), x=COL["product_revenue"], y=COL["product_name"], orientation="h")
#         fig.update_traces(marker_color=CHART_COLORWAY[0])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     with col2:
#         section_label("Top products by profit")
#         if not top_profit.empty:
#             fig = px.bar(top_profit.sort_values(COL["product_profit"]), x=COL["product_profit"], y=COL["product_name"], orientation="h")
#             fig.update_traces(marker_color=CHART_COLORWAY[1])
#             st.plotly_chart(style_fig(fig), use_container_width=True)
#         else:
#             st.info("No profit column found for products.")

#     if COL["product_qty"] in df.columns:
#         section_label("Units sold")
#         top_qty = df.sort_values(COL["product_qty"], ascending=False).head(10)
#         fig = px.bar(top_qty.sort_values(COL["product_qty"]), x=COL["product_qty"], y=COL["product_name"], orientation="h")
#         fig.update_traces(marker_color=CHART_COLORWAY[4])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     with st.expander("Product performance — full table"):
#         st.dataframe(df, use_container_width=True)


# def page_territory_analysis():
#     page_header("🌍", "Territory analysis", "Regional performance across revenue, profit and orders")
#     df = load_table("gold_territory_summary")

#     if df.empty:
#         st.warning("gold_territory_summary returned no rows.")
#         return

#     col1, col2 = st.columns(2)
#     with col1:
#         section_label("Revenue by region")
#         fig = px.bar(df.sort_values(COL["territory_revenue"], ascending=False), x=COL["territory"], y=COL["territory_revenue"])
#         fig.update_traces(marker_color=CHART_COLORWAY[0])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     with col2:
#         section_label("Profit by region")
#         if COL["territory_profit"] in df.columns:
#             fig = px.bar(df.sort_values(COL["territory_profit"], ascending=False), x=COL["territory"], y=COL["territory_profit"])
#             fig.update_traces(marker_color=CHART_COLORWAY[1])
#             st.plotly_chart(style_fig(fig), use_container_width=True)
#         else:
#             st.info("No profit column found for territories.")

#     if COL["territory_orders"] in df.columns:
#         section_label("Orders by region")
#         fig = px.bar(df.sort_values(COL["territory_orders"], ascending=False), x=COL["territory"], y=COL["territory_orders"])
#         fig.update_traces(marker_color=CHART_COLORWAY[4])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     ranked = df.sort_values(COL["territory_revenue"], ascending=False)
#     c1, c2 = st.columns(2)
#     with c1:
#         st.success(f"🏆 Best performing: **{ranked.iloc[0][COL['territory']]}**")
#     with c2:
#         st.error(f"⚠️ Worst performing: **{ranked.iloc[-1][COL['territory']]}**")

#     with st.expander("Territory — full table"):
#         st.dataframe(df, use_container_width=True)


# def page_returns_analysis():
#     page_header("↩️", "Returns analysis", "Where returns are concentrated, by product and category")
#     df = load_table("gold_return_summary")

#     if df.empty:
#         st.warning("gold_return_summary returned no rows.")
#         return

#     col1, col2 = st.columns(2)
#     with col1:
#         section_label("Products with highest returns")
#         top_returns = df.sort_values(COL["return_qty"], ascending=False).head(10)
#         fig = px.bar(top_returns.sort_values(COL["return_qty"]), x=COL["return_qty"], y=COL["return_product"], orientation="h")
#         fig.update_traces(marker_color=CHART_COLORWAY[3])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     with col2:
#         if COL["return_category"] in df.columns:
#             section_label("Category return performance")
#             cat = df.groupby(COL["return_category"], as_index=False)[COL["return_qty"]].sum()
#             fig = px.pie(cat, names=COL["return_category"], values=COL["return_qty"], hole=0.45)
#             st.plotly_chart(style_fig(fig), use_container_width=True)
#         else:
#             st.info("No category column found in gold_return_summary.")

#     if COL["return_rate"] in df.columns:
#         high_return = df[df[COL["return_rate"]] >= df[COL["return_rate"]].mean() + df[COL["return_rate"]].std()]
#         if not high_return.empty:
#             section_label("🚨 Return alerts — unusually high return rates")
#             st.dataframe(high_return.sort_values(COL["return_rate"], ascending=False), use_container_width=True)

#     with st.expander("Returns — full table"):
#         st.dataframe(df, use_container_width=True)


# def page_churn_prediction():
#     page_header("🔮", "Churn prediction", "Active vs. churned customers and who's at risk")
#     df = load_table("gold_customer_churn")

#     if df.empty:
#         st.warning("gold_customer_churn returned no rows.")
#         return

#     status_col = COL["churn_status"]
#     if status_col in df.columns:
#         churned = df[df[status_col].astype(str).str.lower().str.contains("churn")]
#         active = df[~df.index.isin(churned.index)]
#     else:
#         churned, active = pd.DataFrame(), df

#     total_customers = len(df)
#     churn_count = len(churned)
#     active_count = len(active)
#     churn_rate = (churn_count / total_customers * 100) if total_customers else 0

#     c1, c2, c3 = st.columns(3)
#     with c1:
#         kpi_card("Active Customers", fmt_number(active_count), icon="✅", accent="#0EA5A6", accent_soft="#ECFEFF")
#     with c2:
#         kpi_card("Churned Customers", fmt_number(churn_count), icon="⚠️", accent="#EF4444", accent_soft="#FEF2F2")
#     with c3:
#         kpi_card("Churn Rate", fmt_percent(churn_rate), icon="📉", accent="#F59E0B", accent_soft="#FFFBEB")

#     st.write("")

#     col1, col2 = st.columns(2)
#     with col1:
#         section_label("Active vs churned")
#         fig = go.Figure(data=[go.Pie(
#             labels=["Active", "Churned"], values=[active_count, churn_count], hole=0.55,
#             marker=dict(colors=[CHART_COLORWAY[1], CHART_COLORWAY[3]]),
#         )])
#         st.plotly_chart(style_fig(fig), use_container_width=True)

#     with col2:
#         if COL["churn_recency"] in df.columns:
#             section_label("Recency distribution (days since last purchase)")
#             fig = px.histogram(df, x=COL["churn_recency"], nbins=30, color=status_col if status_col in df.columns else None)
#             st.plotly_chart(style_fig(fig), use_container_width=True)

#     section_label("Churn-risk customers")
#     status_options = ["All"] + (sorted(df[status_col].dropna().unique().tolist()) if status_col in df.columns else [])
#     chosen = st.selectbox("Filter by churn status", status_options, label_visibility="collapsed")
#     filtered = df if chosen == "All" or status_col not in df.columns else df[df[status_col] == chosen]

#     if COL["churn_recency"] in filtered.columns:
#         filtered = filtered.sort_values(COL["churn_recency"], ascending=False)

#     st.dataframe(filtered, use_container_width=True)


# def gather_aggregated_metrics() -> dict:
#     """Collect ONLY aggregated business metrics for the AI insights prompt —
#     never raw per-customer rows."""
#     kpi_df = load_table("gold_kpi")
#     monthly_df = load_table("gold_monthly_revenue")
#     category_df = load_table("gold_category_summary")
#     territory_df = load_table("gold_territory_summary")
#     return_df = load_table("gold_return_summary")
#     churn_df = load_table("gold_customer_churn")
#     product_df = load_table("gold_product_summary")

#     total_revenue = safe_first(kpi_df, "kpi_revenue") if not kpi_df.empty else safe_sum(monthly_df, "month_revenue")
#     total_profit = safe_first(kpi_df, "kpi_profit") if not kpi_df.empty else safe_sum(monthly_df, "month_profit")
#     total_orders = safe_first(kpi_df, "kpi_orders")
#     total_customers = safe_first(kpi_df, "kpi_customers")

#     revenue_trend_pct = None
#     profit_trend_pct = None
#     if not monthly_df.empty and COL["month"] in monthly_df.columns:
#         m = sorted_monthly(monthly_df)
#         if len(m) >= 2:
#             prev_rev, last_rev = m[COL["month_revenue"]].iloc[-2], m[COL["month_revenue"]].iloc[-1]
#             if prev_rev:
#                 revenue_trend_pct = (last_rev - prev_rev) / prev_rev * 100
#             if COL["month_profit"] in m.columns:
#                 prev_p, last_p = m[COL["month_profit"]].iloc[-2], m[COL["month_profit"]].iloc[-1]
#                 if prev_p:
#                     profit_trend_pct = (last_p - prev_p) / prev_p * 100

#     top_categories = []
#     if not category_df.empty:
#         top_categories = (
#             category_df.sort_values(COL["category_revenue"], ascending=False)
#             .head(5)[[COL["category"], COL["category_revenue"]]]
#             .to_dict("records")
#         )

#     territory_perf = []
#     worst_territory = None
#     if not territory_df.empty:
#         t_sorted = territory_df.sort_values(COL["territory_revenue"], ascending=False)
#         territory_perf = t_sorted[[COL["territory"], COL["territory_revenue"]]].to_dict("records")
#         worst_territory = t_sorted.iloc[-1][COL["territory"]]

#     avg_return_rate = None
#     top_returned_products = []
#     if not return_df.empty:
#         if COL["return_rate"] in return_df.columns:
#             avg_return_rate = float(return_df[COL["return_rate"]].mean())
#         top_returned_products = (
#             return_df.sort_values(COL["return_qty"], ascending=False)
#             .head(5)[[COL["return_product"], COL["return_qty"]]]
#             .to_dict("records")
#         )

#     churn_rate, churned_count, high_recency_customers = None, None, None
#     if not churn_df.empty:
#         status_col = COL["churn_status"]
#         if status_col in churn_df.columns:
#             churned = churn_df[churn_df[status_col].astype(str).str.lower().str.contains("churn")]
#             churned_count = len(churned)
#             churn_rate = churned_count / len(churn_df) * 100 if len(churn_df) else 0
#         if COL["churn_recency"] in churn_df.columns:
#             threshold = churn_df[COL["churn_recency"]].quantile(0.9)
#             high_recency_customers = int((churn_df[COL["churn_recency"]] >= threshold).sum())

#     top_products = []
#     if not product_df.empty:
#         top_products = (
#             product_df.sort_values(COL["product_revenue"], ascending=False)
#             .head(5)[[COL["product_name"], COL["product_revenue"]]]
#             .to_dict("records")
#         )

#     metrics = {
#         "total_revenue": total_revenue,
#         "total_profit": total_profit,
#         "total_orders": total_orders,
#         "total_customers": total_customers,
#         "revenue_trend_pct": revenue_trend_pct,
#         "profit_trend_pct": profit_trend_pct,
#         "top_categories": top_categories,
#         "territory_performance": territory_perf,
#         "worst_territory": worst_territory,
#         "avg_return_rate": avg_return_rate,
#         "top_returned_products": top_returned_products,
#         "churn_rate": churn_rate,
#         "churned_customers": churned_count,
#         "high_recency_customers": high_recency_customers,
#         "top_products": top_products,
#         "generated_at": datetime.now().isoformat(timespec="seconds"),
#     }
#     return metrics


# SYSTEM_PROMPT = """You are a Business Intelligence Analyst.

# Analyze the supplied business metrics and provide practical, data-driven recommendations.

# Identify:
# 1. Revenue performance
# 2. Profit performance
# 3. Customer behavior
# 4. Customer churn risk
# 5. Product/category performance
# 6. Territory performance
# 7. Return trends
# 8. Important business alerts

# For every important issue provide:

# Priority: HIGH / MEDIUM / LOW
# Issue:
# Evidence:
# Business Impact:
# Recommended Action:

# Then provide:

# ## Executive Summary
# 3-5 key observations.

# ## Positive Trends
# Important opportunities.

# ## Risks & Alerts
# Important business risks.

# ## Customer Insights
# Customer behavior and churn observations.

# ## Recommended Actions
# Top 5 practical management actions.

# Rules:
# - Never invent numbers.
# - Use only the supplied metrics.
# - Use actual numbers whenever available.
# - Do not claim causation unless supported by the data.
# - Keep recommendations practical and business-focused."""


# GEMINI_MODEL = "gemini-2.5-flash"  # kept on Google's free tier — gemini-2.0-flash was deprecated


# def call_gemini(system_prompt: str, user_message: str, history: list = None) -> str:
#     """Call Google Gemini (free tier). history is an optional list of
#     {"role": "user"|"model", "text": ...} dicts for multi-turn chat."""
#     import google.generativeai as genai

#     genai.configure(api_key=get_secret("GEMINI_API_KEY", required=True))
#     model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=system_prompt)

#     if history:
#         chat = model.start_chat(history=[
#             {"role": h["role"], "parts": [h["text"]]} for h in history
#         ])
#         response = chat.send_message(user_message)
#     else:
#         response = model.generate_content(user_message)

#     return response.text.strip()


# def call_ai_for_insights(metrics: dict) -> str:
#     user_message = (
#         "Here are the aggregated business metrics (JSON). "
#         "Analyze them and follow the system instructions exactly.\n\n"
#         f"{metrics}"
#     )
#     return call_gemini(SYSTEM_PROMPT, user_message)


# def page_ai_insights():
#     page_header("🤖", "AI business insights", "Powered by Google Gemini (free tier) — analysis runs only on aggregated KPIs, never raw customer-level data")

#     if st.button("Generate AI Insights", type="primary"):
#         with st.spinner("Gemini is analyzing your business metrics…"):
#             try:
#                 metrics = gather_aggregated_metrics()
#                 insight_text = call_ai_for_insights(metrics)
#                 st.session_state["ai_insights"] = insight_text
#                 st.session_state["ai_insights_metrics"] = metrics
#             except KeyError:
#                 st.error(
#                     "GEMINI_API_KEY is missing from your Streamlit secrets. "
#                     "Add it to .streamlit/secrets.toml and restart the app."
#                 )
#             except Exception as e:
#                 st.error(f"Could not generate AI insights right now.\n\nDetails: {e}")

#     if "ai_insights" in st.session_state:
#         st.markdown("### 🤖 AI Business Insights")
#         st.markdown(st.session_state["ai_insights"])

#         with st.expander("Rule-based alerts (computed locally, not by Gemini)"):
#             m = st.session_state.get("ai_insights_metrics", {})
#             render_alerts(compute_alerts(m))

#         with st.expander("Raw aggregated metrics sent to Gemini"):
#             st.json(st.session_state.get("ai_insights_metrics", {}))
#     else:
#         st.info("Click **Generate AI Insights** to run the analysis.")


# CHAT_SYSTEM_PROMPT = """You are a helpful Business Intelligence assistant embedded in a
# Streamlit dashboard called "Customer & Revenue Intelligence Platform".

# You have been given a snapshot of the company's aggregated KPIs (revenue, profit,
# category/territory performance, returns, churn, top products) as context below.
# Answer the user's questions using this data whenever relevant. If a question asks
# for something not present in the data, say so honestly rather than inventing numbers.
# Keep answers concise and business-focused. Never invent figures.

# Aggregated business metrics snapshot:
# {metrics}
# """


# def page_ai_chat():
#     page_header("💬", "AI chat", "Ask questions about your business metrics — powered by Google Gemini (free tier)")

#     if "chat_history" not in st.session_state:
#         st.session_state["chat_history"] = []  # list of {"role": "user"/"model", "text": ...}

#     if st.button("🔄 Reset conversation"):
#         st.session_state["chat_history"] = []
#         st.rerun()

#     for turn in st.session_state["chat_history"]:
#         with st.chat_message("user" if turn["role"] == "user" else "assistant"):
#             st.markdown(turn["text"])

#     prompt = st.chat_input("Ask about revenue, churn, top products, territories…")
#     if prompt:
#         st.session_state["chat_history"].append({"role": "user", "text": prompt})
#         with st.chat_message("user"):
#             st.markdown(prompt)

#         with st.chat_message("assistant"):
#             with st.spinner("Thinking…"):
#                 try:
#                     metrics = gather_aggregated_metrics()
#                     system_prompt = CHAT_SYSTEM_PROMPT.format(metrics=metrics)
#                     # history excludes the message we're about to send
#                     reply = call_gemini(
#                         system_prompt,
#                         prompt,
#                         history=st.session_state["chat_history"][:-1],
#                     )
#                 except KeyError:
#                     reply = (
#                         "⚠️ GEMINI_API_KEY is missing from your Streamlit secrets. "
#                         "Add it to .streamlit/secrets.toml and restart the app."
#                     )
#                 except Exception as e:
#                     reply = f"⚠️ Could not get a response right now.\n\nDetails: {e}"
#                 st.markdown(reply)
#         st.session_state["chat_history"].append({"role": "model", "text": reply})


# # ==========================================================================
# # 6. LOGIN
# # ==========================================================================


# def login_page():
#     """Simple login gate. Credentials come from st.secrets — never hardcoded."""
#     st.markdown(
#         textwrap.dedent(
#             """
#         <style>
#         [data-testid="stAppViewContainer"] > .main {
#             background: linear-gradient(135deg, #1DD3B0 0%, #6C63FF 55%, #FF6B9D 100%);
#         }
#         </style>
#         """
#         ),
#         unsafe_allow_html=True,
#     )

#     _, mid, _ = st.columns([1, 1.1, 1])
#     with mid:
#         st.write("")
#         st.write("")
#         with st.container(border=True):
#             st.markdown('<div class="login-title">Revenue Intelligence</div>', unsafe_allow_html=True)
#             st.markdown('<div class="login-sub">Sign in to view your dashboards</div>', unsafe_allow_html=True)

#             with st.form("login_form", border=False):
#                 username = st.text_input("Username", placeholder="Username")
#                 password = st.text_input("Password", type="password", placeholder="Password")
#                 submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

#             if submitted:
#                 valid_user = get_secret("APP_USERNAME", "admin")
#                 valid_pass = get_secret("APP_PASSWORD", "admin123")
#                 if username == valid_user and password == valid_pass:
#                     st.session_state["authenticated"] = True
#                     st.session_state["username"] = username
#                     st.rerun()
#                 else:
#                     st.error("Incorrect username or password.")


# # ==========================================================================
# # 6b. HOME, REPORTS & SETTINGS
# # ==========================================================================


# def page_home():
#     page_header("🏠", "Home", "Quick summary and shortcuts to every section")

#     kpi_df = load_table("gold_kpi")
#     total_revenue = safe_first(kpi_df, "kpi_revenue")
#     total_profit = safe_first(kpi_df, "kpi_profit")
#     total_orders = safe_first(kpi_df, "kpi_orders")
#     total_customers = safe_first(kpi_df, "kpi_customers")

#     c1, c2, c3, c4 = st.columns(4)
#     with c1:
#         kpi_card("Total Revenue", fmt_currency(total_revenue), icon="💰", accent="#14B8A6")
#     with c2:
#         kpi_card("Total Profit", fmt_currency(total_profit), icon="📈", accent="#818CF8")
#     with c3:
#         kpi_card("Total Orders", fmt_number(total_orders), icon="🧾", accent="#F59E0B")
#     with c4:
#         kpi_card("Total Customers", fmt_number(total_customers), icon="👥", accent="#22D3EE")

#     alerts = compute_alerts(gather_aggregated_metrics())
#     if alerts:
#         st.write("")
#         section_label(f"⚠️ Active alerts ({len(alerts)})")
#         render_alerts(alerts)

#     st.write("")
#     section_label("Jump to a section")

#     tiles = [
#         ("📈", "Executive Overview", "Company-wide revenue, profit and demand"),
#         ("👥", "Customer Intelligence", "Top customers and revenue concentration"),
#         ("📦", "Product Intelligence", "Best sellers by revenue, profit, volume"),
#         ("🌍", "Territory Analysis", "Regional performance breakdown"),
#         ("↩️", "Returns Analysis", "Where returns are concentrated"),
#         ("🔮", "Churn Prediction", "Active vs. churned, who's at risk"),
#         ("🤖", "AI Business Insights", "Gemini-generated analysis of your KPIs"),
#         ("💬", "AI Chat", "Ask questions about your metrics"),
#     ]
#     cols = st.columns(4)
#     for i, (icon, title, desc) in enumerate(tiles):
#         with cols[i % 4]:
#             st.markdown(
#                 textwrap.dedent(
#                     f"""
#                 <div class="kpi-card" style="min-height:110px;">
#                     <div class="kpi-icon">{icon}</div>
#                     <div class="kpi-label" style="text-transform:none;font-size:0.85rem;margin-top:10px;">{title}</div>
#                     <div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:4px;">{desc}</div>
#                 </div>
#                 """
#                 ),
#                 unsafe_allow_html=True,
#             )


# def page_reports():
#     page_header("📤", "Reports & export", "Preview any gold table and download it as CSV")

#     table_key = st.selectbox("Choose a table", list(TABLES.keys()))
#     df = load_table(table_key)

#     if df.empty:
#         st.warning(f"{table_key} returned no rows.")
#         return

#     c1, c2 = st.columns(2)
#     with c1:
#         kpi_card("Rows", fmt_number(len(df)), icon="📊", accent="#14B8A6")
#     with c2:
#         kpi_card("Columns", fmt_number(len(df.columns)), icon="🧮", accent="#818CF8")

#     st.write("")
#     section_label("Preview")
#     st.dataframe(df.head(200), use_container_width=True)

#     csv_bytes = df.to_csv(index=False).encode("utf-8")
#     st.download_button(
#         "⬇️ Download full table as CSV",
#         data=csv_bytes,
#         file_name=f"{table_key}.csv",
#         mime="text/csv",
#         type="primary",
#     )


# def page_settings():
#     page_header("⚙️", "Settings", "App configuration and cache controls")

#     section_label("Connection")
#     st.markdown(f"**Catalog:** `{CATALOG}`  \n**Schema:** `{SCHEMA}`")

#     st.write("")
#     section_label("Cache")
#     st.markdown(f"Query results are cached for **{REFRESH_TTL_SECONDS // 60} minutes** before Databricks is queried again.")
#     if st.button("🧹 Clear all cached data now", type="primary"):
#         st.cache_data.clear()
#         st.success("Cache cleared. Data will reload fresh on next page view.")

#     st.write("")
#     section_label("Column mapping")
#     st.caption("If a chart looks empty or a page errors, the most common cause is a column name mismatch. Edit the `COL` dictionary near the top of app.py to match your actual gold table columns.")
#     with st.expander("View current column mapping"):
#         st.json(COL)

#     st.write("")
#     section_label("About")
#     st.caption("Customer & Revenue Intelligence Platform — Databricks gold layer + Streamlit + Google Gemini (free tier).")


# # ==========================================================================
# # 7. SIDEBAR NAVIGATION
# # ==========================================================================

# NAV_GROUPS = [
#     ("OVERVIEW", {
#         "🏠  Home": page_home,
#         "📈  Executive Overview": page_executive_overview,
#     }),
#     ("ANALYSIS", {
#         "👥  Customer Intelligence": page_customer_intelligence,
#         "📦  Product Intelligence": page_product_intelligence,
#         "🌍  Territory Analysis": page_territory_analysis,
#         "↩️  Returns Analysis": page_returns_analysis,
#         "🔮  Churn Prediction": page_churn_prediction,
#     }),
#     ("AI TOOLS", {
#         "🤖  AI Business Insights": page_ai_insights,
#         "💬  AI Chat": page_ai_chat,
#     }),
#     ("MORE", {
#         "📤  Reports & Export": page_reports,
#         "⚙️  Settings": page_settings,
#     }),
# ]

# PAGES = {label: fn for _, group in NAV_GROUPS for label, fn in group.items()}


# def main():
#     if not st.session_state.get("authenticated", False):
#         login_page()
#         return

#     st.sidebar.markdown(
#         textwrap.dedent(
#             """
#         <div class="sidebar-brand">
#             <div>
#                 <div class="name">Revenue Intelligence</div>
#                 <div class="tagline">Customer & Revenue Platform</div>
#             </div>
#         </div>
#         """
#         ),
#         unsafe_allow_html=True,
#     )
#     choice = st.session_state.get("current_page", "🏠  Home")
#     if choice not in PAGES:
#         choice = "🏠  Home"

#     for group_name, group_pages in NAV_GROUPS:
#         st.sidebar.markdown(
#             f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.06em;'
#             f'color:{TEXT_MUTED};margin:14px 0 4px 4px;">{group_name}</div>',
#             unsafe_allow_html=True,
#         )
#         for label in group_pages:
#             is_active = label == choice
#             if st.sidebar.button(
#                 label,
#                 key=f"nav_{label}",
#                 use_container_width=True,
#                 type="primary" if is_active else "secondary",
#             ):
#                 st.session_state["current_page"] = label
#                 st.rerun()

#     st.sidebar.markdown("---")
#     if st.sidebar.button("🔄 Refresh data", use_container_width=True):
#         st.cache_data.clear()
#         st.rerun()
#     if st.sidebar.button("🚪 Log out", use_container_width=True):
#         st.session_state["authenticated"] = False
#         st.session_state.pop("username", None)
#         st.rerun()
#     st.sidebar.caption(f"Cache TTL: {REFRESH_TTL_SECONDS // 60} min · Last loaded: {datetime.now().strftime('%H:%M:%S')}")

#     st.sidebar.markdown(
#         textwrap.dedent(
#             f"""
#         <div class="sidebar-profile">
#             <div class="dot"></div>
#             <div>
#                 <div class="who">{st.session_state.get('username', 'User')}</div>
#                 <div class="role">Signed in</div>
#             </div>
#         </div>
#         """
#         ),
#         unsafe_allow_html=True,
#     )

#     PAGES[choice]()


# if __name__ == "__main__":
#     main()





"""
Customer & Revenue Intelligence Platform
-----------------------------------------
A Streamlit dashboard that reads Gold-layer tables from a Databricks SQL
Warehouse (catalog: workspace, schema: default) and mirrors the
Power BI report, plus an AI Business Insights page powered by Google Gemini.

Run with:  streamlit run app.py
"""

import time
import textwrap
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from databricks import sql as databricks_sql

# ==========================================================================
# 0. CONFIG — CATALOG / SCHEMA / COLUMN NAMES
# --------------------------------------------------------------------------
CATALOG = "workspace"
SCHEMA = "default"

TABLES = {
    "gold_kpi": f"{CATALOG}.{SCHEMA}.gold_kpi",
    "gold_monthly_revenue": f"{CATALOG}.{SCHEMA}.gold_monthly_revenue",
    "gold_customer_summary": f"{CATALOG}.{SCHEMA}.gold_customer_summary",
    "gold_product_summary": f"{CATALOG}.{SCHEMA}.gold_product_summary",
    "gold_category_summary": f"{CATALOG}.{SCHEMA}.gold_category_summary",
    "gold_territory_summary": f"{CATALOG}.{SCHEMA}.gold_territory_summary",
    "gold_return_summary": f"{CATALOG}.{SCHEMA}.gold_return_summary",
    "gold_customer_churn": f"{CATALOG}.{SCHEMA}.gold_customer_churn",
}

COL = {
    # gold_kpi
    "kpi_revenue": "TotalRevenue",
    "kpi_profit": "TotalProfit",
    "kpi_orders": "TotalOrders",
    "kpi_customers": "TotalCustomers",
    "kpi_quantity": "TotalQuantity",
    # gold_monthly_revenue
    "year": "Year",
    "month": "Month",
    "month_revenue": "Revenue",
    "month_profit": "Profit",
    # gold_category_summary
    "category": "CategoryName",
    "category_revenue": "TotalRevenue",
    "category_profit": "TotalProfit",
    # gold_territory_summary
    "territory": "Region",
    "territory_revenue": "TotalRevenue",
    "territory_profit": "TotalProfit",
    "territory_orders": "TotalOrders",
    # gold_customer_summary
    "customer_name": "CustomerKey",
    "customer_revenue": "TotalRevenue",
    "customer_orders": "TotalOrders",
    # gold_product_summary
    "product_name": "ProductKey",
    "product_revenue": "TotalRevenue",
    "product_profit": "TotalProfit",
    "product_qty": "UnitsSold",
    # gold_return_summary
    "return_product": "ProductName",
    "return_category": "CategoryName",
    "return_qty": "TotalReturnedQuantity",
    "return_rate": "ReturnRate",
    # gold_customer_churn
    "churn_customer": "CustomerKey",
    "churn_status": "ChurnStatus",
    "churn_recency": "RecencyDays",
    "churn_revenue": "TotalRevenue",
}

REFRESH_TTL_SECONDS = 600

# ==========================================================================
# 1. PAGE CONFIG & STYLING
# ==========================================================================

st.set_page_config(
    page_title="Customer & Revenue Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

ACCENT = "#14B8A6"
BG_DARK = "#0B1220"
CARD_DARK = "#141B2E"
BORDER_DARK = "rgba(255,255,255,0.08)"
TEXT_LIGHT = "#E5E7EB"
TEXT_MUTED = "#94A3B8"
NAVY = "#0F1729"
CTA_GRADIENT = "linear-gradient(135deg, #FF7676 0%, #FF9A5A 100%)"

CHART_COLORWAY = ["#22D3EE", "#14B8A6", "#F472B6", "#F59E0B", "#818CF8", "#84CC16"]

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}

    [data-testid="stAppViewContainer"] > .main {{
        background:
            radial-gradient(circle at 0% 15%, rgba(34,211,238,0.10), transparent 35%),
            radial-gradient(circle at 100% 15%, rgba(244,114,182,0.10), transparent 35%),
            {BG_DARK};
    }}
    [data-testid="stHeader"] {{ background: transparent; }}

    .page-header {{ margin-bottom: 6px; }}
    .page-header h1 {{ font-size: 1.55rem; font-weight: 700; color: {TEXT_LIGHT}; margin: 0; line-height: 1.2; }}
    .page-header p {{ font-size: 0.9rem; color: {TEXT_MUTED}; margin: 2px 0 0 0; }}
    .page-divider {{ border: none; border-top: 1px solid {BORDER_DARK}; margin: 14px 0 20px 0; }}

    .kpi-card {{
        position: relative;
        background: {CARD_DARK};
        border: 1px solid {BORDER_DARK};
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.25);
        transition: box-shadow 0.15s ease, transform 0.15s ease;
        overflow: hidden;
    }}
    .kpi-card:hover {{ box-shadow: 0 8px 26px rgba(0,0,0,0.35); transform: translateY(-1px); }}
    .kpi-card::before {{
        content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
        background: var(--kpi-accent, {ACCENT});
    }}
    .kpi-top {{ display: flex; align-items: center; justify-content: space-between; }}
    .kpi-icon {{
        width: 30px; height: 30px; border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 15px; background: rgba(255,255,255,0.06); color: var(--kpi-accent, {ACCENT});
    }}
    .kpi-label {{
        font-size: 0.72rem; color: {TEXT_MUTED}; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.04em; margin-top: 10px;
    }}
    .kpi-value {{
        font-size: 1.55rem; font-weight: 700; color: {TEXT_LIGHT};
        margin-top: 2px; letter-spacing: -0.01em;
    }}

    .alert-high {{background:rgba(220,38,38,0.14); border-left:4px solid #f87171; padding:12px 14px; border-radius:8px; margin-bottom:8px; color:#fecaca;}}
    .alert-medium {{background:rgba(217,119,6,0.14); border-left:4px solid #fbbf24; padding:12px 14px; border-radius:8px; margin-bottom:8px; color:#fde68a;}}
    .alert-low {{background:rgba(37,99,235,0.14); border-left:4px solid #60a5fa; padding:12px 14px; border-radius:8px; margin-bottom:8px; color:#bfdbfe;}}

    .section-label {{ font-size: 0.95rem; font-weight: 600; color: {TEXT_LIGHT}; margin-bottom: 4px; margin-top: 6px; }}

    div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"], div[data-testid="stExpander"] {{
        background: {CARD_DARK}; border: 1px solid {BORDER_DARK}; border-radius: 14px; padding: 6px;
    }}

    section[data-testid="stSidebar"] {{background-color: {NAVY}; border-right: 1px solid {BORDER_DARK};}}
    section[data-testid="stSidebar"] * {{color: {TEXT_LIGHT} !important;}}
    section[data-testid="stSidebar"] hr {{border-color: rgba(255,255,255,0.08);}}
    .sidebar-brand {{ padding: 4px 0 16px 0; }}
    .sidebar-brand .name {{ font-size: 0.95rem; font-weight: 700; line-height: 1.15; }}
    .sidebar-brand .tagline {{ font-size: 0.72rem; color: {TEXT_MUTED} !important; }}
    div[data-testid="stSidebar"] div[role="radiogroup"] label {{
        padding: 8px 12px; border-radius: 10px; margin-bottom: 2px; transition: background 0.15s ease;
    }}
    div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: #ffffff !important;
    }}
    div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
        color: {BG_DARK} !important; font-weight: 600;
    }}
    .sidebar-profile {{
        display: flex; align-items: center; gap: 10px;
        background: rgba(255,255,255,0.05); border: 1px solid {BORDER_DARK};
        border-radius: 12px; padding: 10px 12px; margin-top: 10px;
    }}
    .sidebar-profile .dot {{
        width: 8px; height: 8px; border-radius: 50%; background: #4ade80; flex-shrink: 0;
        box-shadow: 0 0 0 3px rgba(74,222,128,0.18);
    }}
    .sidebar-profile .who {{ font-size: 0.78rem; font-weight: 600; line-height: 1.2; }}
    .sidebar-profile .role {{ font-size: 0.68rem; color: {TEXT_MUTED} !important; }}

    .stButton > button {{
        border-radius: 8px; font-weight: 600; border: 1px solid {BORDER_DARK};
        background: {CARD_DARK}; color: {TEXT_LIGHT};
    }}
    .stButton > button[kind="primary"] {{
        background: {CTA_GRADIENT}; border: none; color: #ffffff;
        border-radius: 999px; box-shadow: 0 6px 16px rgba(255, 118, 118, 0.35);
    }}
    .stButton > button[kind="primary"]:hover {{ opacity: 0.92; color: #ffffff; }}
    section[data-testid="stSidebar"] .stButton > button {{
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
        border-radius: 8px;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 20px !important; box-shadow: 0 20px 60px rgba(0,0,0,0.4);
    }}
    .login-title {{ text-align: center; font-size: 1.25rem; font-weight: 700; color: #111827; margin-bottom: 2px; margin-top: 4px; }}
    .login-sub {{ text-align: center; font-size: 0.85rem; color: #6b7280; margin-bottom: 20px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = CHART_COLORWAY


def style_fig(fig):
    fig.update_layout(
        margin=dict(l=15, r=15, t=25, b=15),
        font=dict(family="Inter, sans-serif", size=12, color=TEXT_MUTED),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=CARD_DARK, font_size=12, font_color=TEXT_LIGHT),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor="rgba(255,255,255,0.15)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False)
    return fig


def page_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="page-header">
            <div>
                <h1>{title}</h1>
                {f'<p>{subtitle}</p>' if subtitle else ''}
            </div>
        </div>
        <hr class="page-divider" />
        """,
        unsafe_allow_html=True,
    )

# ==========================================================================
# 2. DATABRICKS CONNECTION
# ==========================================================================

def get_secret(key: str, default=None, required: bool = False):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    if required:
        st.error(f"Missing secret **`{key}`** in `.streamlit/secrets.toml`.")
        st.stop()
    return default


@st.cache_resource(show_spinner=False)
def get_connection():
    return databricks_sql.connect(
        server_hostname=get_secret("DATABRICKS_SERVER_HOSTNAME", required=True),
        http_path=get_secret("DATABRICKS_HTTP_PATH", required=True),
        access_token=get_secret("DATABRICKS_TOKEN", required=True),
    )


@st.cache_data(ttl=REFRESH_TTL_SECONDS, show_spinner="Reading data from Databricks…")
def run_query(query: str) -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=columns)


def load_table(table_key: str) -> pd.DataFrame:
    full_name = TABLES[table_key]
    try:
        return run_query(f"SELECT * FROM {full_name}")
    except Exception as e:
        st.error(f"Could not read `{full_name}` from Databricks.\n\nDetails: {e}")
        return pd.DataFrame()


def col(df: pd.DataFrame, key: str):
    name = COL.get(key)
    if name and name in df.columns:
        return df[name]
    return None


def safe_sum(df: pd.DataFrame, key: str) -> float:
    series = col(df, key)
    return float(series.sum()) if series is not None else 0.0


def safe_first(df: pd.DataFrame, key: str, default=0):
    series = col(df, key)
    if series is not None and len(series) > 0:
        return series.iloc[0]
    return default


def sorted_monthly(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if COL["year"] in df.columns and COL["month"] in df.columns:
        df = df.sort_values([COL["year"], COL["month"]])
        df["Period"] = df[COL["year"]].astype(str) + "-" + df[COL["month"]].astype(str).str.zfill(2)
    elif COL["month"] in df.columns:
        df = df.sort_values(COL["month"])
        df["Period"] = df[COL["month"]]
    return df

# ==========================================================================
# 3. UI HELPERS
# ==========================================================================

def kpi_card(label: str, value: str, icon: str = "📊", accent: str = None, accent_soft: str = None):
    style_vars = ""
    if accent:
        style_vars += f"--kpi-accent:{accent};"
    if accent_soft:
        style_vars += f"--kpi-accent-soft:{accent_soft};"
    st.markdown(
        f"""
        <div class="kpi-card" style="{style_vars}">
            <div class="kpi-top">
                <div class="kpi-icon">{icon}</div>
            </div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def fmt_currency(x: float) -> str:
    try:
        return f"${x:,.0f}"
    except Exception:
        return str(x)


def fmt_number(x: float) -> str:
    try:
        return f"{x:,.0f}"
    except Exception:
        return str(x)


def fmt_percent(x: float) -> str:
    try:
        return f"{x:.1f}%"
    except Exception:
        return str(x)


def render_alerts(alerts: list):
    if not alerts:
        st.success("No alerts — all monitored metrics look healthy.")
        return
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for a in sorted(alerts, key=lambda x: priority_order.get(x["priority"], 3)):
        css_class = f"alert-{a['priority'].lower()}"
        st.markdown(
            f"""
            <div class="{css_class}">
                <b>{a['priority']} — {a['title']}</b><br/>
                {a['detail']}
            </div>
            """,
            unsafe_allow_html=True,
        )

# ==========================================================================
# 4. ALERT LOGIC
# ==========================================================================

def compute_alerts(metrics: dict) -> list:
    alerts = []
    churn_rate = metrics.get("churn_rate")
    if churn_rate is not None and churn_rate >= 25:
        alerts.append({"priority": "HIGH", "title": "High churn rate", "detail": f"Churn rate is {churn_rate:.1f}%."})
    elif churn_rate is not None and churn_rate >= 15:
        alerts.append({"priority": "MEDIUM", "title": "Elevated churn rate", "detail": f"Churn rate is {churn_rate:.1f}%."})

    rev_trend = metrics.get("revenue_trend_pct")
    if rev_trend is not None and rev_trend <= -10:
        alerts.append({"priority": "HIGH", "title": "Revenue decline", "detail": f"Revenue is down {abs(rev_trend):.1f}%."})

    profit_trend = metrics.get("profit_trend_pct")
    if profit_trend is not None and profit_trend <= -10:
        alerts.append({"priority": "HIGH", "title": "Profit decline", "detail": f"Profit is down {abs(profit_trend):.1f}%."})

    return_rate = metrics.get("avg_return_rate")
    if return_rate is not None and return_rate >= 10:
        alerts.append({"priority": "HIGH", "title": "High product returns", "detail": f"Return rate is {return_rate:.1f}%."})

    worst_territory = metrics.get("worst_territory")
    if worst_territory:
        alerts.append({"priority": "LOW", "title": "Underperforming territory", "detail": f"{worst_territory} is lowest-revenue."})

    return alerts

# ==========================================================================
# 5. PAGES
# ==========================================================================

def page_executive_overview():
    page_header("📈", "Executive overview", "Company-wide revenue, profit and demand at a glance")

    kpi_df = load_table("gold_kpi")
    monthly_df = load_table("gold_monthly_revenue")
    category_df = load_table("gold_category_summary")
    territory_df = load_table("gold_territory_summary")

    alerts = compute_alerts(gather_aggregated_metrics())
    if alerts:
        section_label(f"⚠️ Alerts ({len(alerts)})")
        render_alerts(alerts)
        st.write("")

    total_revenue = safe_first(kpi_df, "kpi_revenue") if not kpi_df.empty else safe_sum(monthly_df, "month_revenue")
    total_profit = safe_first(kpi_df, "kpi_profit") if not kpi_df.empty else safe_sum(monthly_df, "month_profit")
    total_orders = safe_first(kpi_df, "kpi_orders")
    total_customers = safe_first(kpi_df, "kpi_customers")
    total_quantity = safe_first(kpi_df, "kpi_quantity")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Revenue", fmt_currency(total_revenue), icon="💰", accent="#4F46E5", accent_soft="#EEF2FF")
    with c2:
        kpi_card("Total Profit", fmt_currency(total_profit), icon="📈", accent="#0EA5A6", accent_soft="#ECFEFF")
    with c3:
        kpi_card("Total Orders", fmt_number(total_orders), icon="🧾", accent="#F59E0B", accent_soft="#FFFBEB")
    with c4:
        kpi_card("Total Customers", fmt_number(total_customers), icon="👥", accent="#0284C7", accent_soft="#F0F9FF")
    with c5:
        kpi_card("Total Quantity", fmt_number(total_quantity), icon="📦", accent="#84CC16", accent_soft="#F7FEE7")

    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        section_label("Revenue trend")
        if not monthly_df.empty and COL["month"] in monthly_df.columns:
            m = sorted_monthly(monthly_df)
            fig = px.line(m, x="Period", y=COL["month_revenue"], markers=True)
            fig.update_traces(line_color=CHART_COLORWAY[0], marker=dict(size=6))
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("No data available in gold_monthly_revenue.")

    with col2:
        section_label("Profit trend")
        if not monthly_df.empty and COL["month"] in monthly_df.columns and COL["month_profit"] in monthly_df.columns:
            m = sorted_monthly(monthly_df)
            fig = px.line(m, x="Period", y=COL["month_profit"], markers=True)
            fig.update_traces(line_color=CHART_COLORWAY[1], marker=dict(size=6))
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("No profit trend data available.")

    col3, col4 = st.columns(2)
    with col3:
        section_label("Revenue by category")
        if not category_df.empty:
            fig = px.bar(
                category_df.sort_values(COL["category_revenue"], ascending=False),
                x=COL["category"], y=COL["category_revenue"],
            )
            fig.update_traces(marker_color=CHART_COLORWAY[0])
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("No data available in gold_category_summary.")

    with col4:
        section_label("Revenue by territory")
        if not territory_df.empty:
            fig = px.bar(
                territory_df.sort_values(COL["territory_revenue"], ascending=False),
                x=COL["territory"], y=COL["territory_revenue"], color=COL["territory"],
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("No data available in gold_territory_summary.")


# ==========================================================================
# CUSTOMER INTELLIGENCE (Upgraded Graphs)
# ==========================================================================
def page_customer_intelligence():
    page_header("👥", "Customer intelligence", "Top spending accounts and customer revenue distribution")
    df = load_table("gold_customer_summary")

    if df.empty:
        st.warning("gold_customer_summary returned no rows.")
        return

    df = df.copy()
    # Format customer display name cleanly: "Cust #11000"
    df["CustomerLabel"] = "Customer #" + df[COL["customer_name"]].astype(str)

    customer_count = len(df)
    total_customer_revenue = safe_sum(df, "customer_revenue")
    avg_revenue_per_cust = total_customer_revenue / customer_count if customer_count else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Total Customers", fmt_number(customer_count), icon="👥", accent="#0284C7", accent_soft="#F0F9FF")
    with c2:
        kpi_card("Total Customer Revenue", fmt_currency(total_customer_revenue), icon="💰", accent="#4F46E5", accent_soft="#EEF2FF")
    with c3:
        kpi_card("Avg Spend / Customer", fmt_currency(avg_revenue_per_cust), icon="💳", accent="#14B8A6", accent_soft="#ECFEFF")

    st.write("")

    top10 = df.sort_values(COL["customer_revenue"], ascending=False).head(10).copy()

    col1, col2 = st.columns([1.1, 0.9])
    with col1:
        section_label("🏆 Top 10 customers by revenue")
        fig = px.bar(
            top10.sort_values(COL["customer_revenue"], ascending=True),
            x=COL["customer_revenue"],
            y="CustomerLabel",
            orientation="h",
            text=COL["customer_revenue"],
            color=COL["customer_revenue"],
            color_continuous_scale="Teal",
        )
        fig.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
            marker_line_width=0,
        )
        fig.update_layout(
            coloraxis_showscale=False,
            xaxis_title="Revenue ($)",
            yaxis_title=None,
        )
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with col2:
        section_label("🍩 Top 10 customer revenue share")
        top10_total = top10[COL["customer_revenue"]].sum()
        other_total = max(0, total_customer_revenue - top10_total)
        share_df = pd.DataFrame({
            "Segment": ["Top 10 Customers", "All Other Customers"],
            "Revenue": [top10_total, other_total],
        })
        fig_donut = px.pie(
            share_df,
            names="Segment",
            values="Revenue",
            hole=0.55,
            color_discrete_sequence=[CHART_COLORWAY[1], "#334155"],
        )
        fig_donut.update_traces(
            textinfo="percent+label",
            pull=[0.05, 0],
            marker=dict(line=dict(color=CARD_DARK, width=2)),
        )
        st.plotly_chart(style_fig(fig_donut), use_container_width=True)

    if COL["customer_orders"] in df.columns:
        st.write("")
        section_label("🎯 Customer orders vs. total spend")
        fig_scatter = px.scatter(
            df.head(200),
            x=COL["customer_orders"],
            y=COL["customer_revenue"],
            color=COL["customer_revenue"],
            color_continuous_scale="Purples",
            hover_name="CustomerLabel",
            size=COL["customer_revenue"],
            size_max=18,
            labels={COL["customer_orders"]: "Orders Count", COL["customer_revenue"]: "Revenue ($)"},
        )
        fig_scatter.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_fig(fig_scatter), use_container_width=True)

    with st.expander("Top customers — detail data table"):
        st.dataframe(top10.drop(columns=["CustomerLabel"], errors="ignore"), use_container_width=True)


# ==========================================================================
# PRODUCT INTELLIGENCE (Upgraded Graphs)
# ==========================================================================
def page_product_intelligence():
    page_header("📦", "Product intelligence", "Best sellers by revenue, profit margin and sales volume")
    df = load_table("gold_product_summary")

    if df.empty:
        st.warning("gold_product_summary returned no rows.")
        return

    df = df.copy()
    df["ProductLabel"] = "Product #" + df[COL["product_name"]].astype(str)

    total_products = len(df)
    total_rev = safe_sum(df, "product_revenue")
    total_prof = safe_sum(df, "product_profit") if COL["product_profit"] in df.columns else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Total Products Sold", fmt_number(total_products), icon="📦", accent="#22D3EE")
    with c2:
        kpi_card("Total Catalog Revenue", fmt_currency(total_rev), icon="💰", accent="#14B8A6")
    with c3:
        kpi_card("Total Product Profit", fmt_currency(total_prof), icon="📈", accent="#818CF8")

    st.write("")

    top10_rev = df.sort_values(COL["product_revenue"], ascending=False).head(10).copy()

    col1, col2 = st.columns([1.1, 0.9])
    with col1:
        section_label("📊 Top 10 products: revenue & profit comparison")
        # Grouped bar chart comparing Revenue and Profit
        melted = top10_rev.melt(
            id_vars=["ProductLabel"],
            value_vars=[COL["product_revenue"], COL["product_profit"]] if COL["product_profit"] in top10_rev.columns else [COL["product_revenue"]],
            var_name="Metric",
            value_name="Amount",
        )
        metric_rename = {COL["product_revenue"]: "Revenue", COL.get("product_profit", ""): "Profit"}
        melted["Metric"] = melted["Metric"].map(lambda x: metric_rename.get(x, x))

        fig_comp = px.bar(
            melted,
            x="ProductLabel",
            y="Amount",
            color="Metric",
            barmode="group",
            color_discrete_map={"Revenue": CHART_COLORWAY[0], "Profit": CHART_COLORWAY[1]},
        )
        fig_comp.update_layout(xaxis_title=None, yaxis_title="Amount ($)")
        st.plotly_chart(style_fig(fig_comp), use_container_width=True)

    with col2:
        section_label("🍩 Top 10 products revenue distribution")
        fig_donut = px.pie(
            top10_rev,
            names="ProductLabel",
            values=COL["product_revenue"],
            hole=0.55,
            color_discrete_sequence=CHART_COLORWAY,
        )
        fig_donut.update_traces(
            textinfo="percent",
            marker=dict(line=dict(color=CARD_DARK, width=2)),
        )
        st.plotly_chart(style_fig(fig_donut), use_container_width=True)

    if COL["product_qty"] in df.columns:
        st.write("")
        section_label("📦 Best sellers by unit sales volume")
        top_qty = df.sort_values(COL["product_qty"], ascending=False).head(10).copy()
        fig_qty = px.bar(
            top_qty.sort_values(COL["product_qty"], ascending=True),
            x=COL["product_qty"],
            y="ProductLabel",
            orientation="h",
            text=COL["product_qty"],
            color=COL["product_qty"],
            color_continuous_scale="Blues",
        )
        fig_qty.update_traces(texttemplate="%{text:,.0f} units", textposition="outside")
        fig_qty.update_layout(coloraxis_showscale=False, xaxis_title="Units Sold", yaxis_title=None)
        st.plotly_chart(style_fig(fig_qty), use_container_width=True)

    with st.expander("Product performance — full data table"):
        st.dataframe(df.drop(columns=["ProductLabel"], errors="ignore"), use_container_width=True)


def page_territory_analysis():
    page_header("🌍", "Territory analysis", "Regional performance across revenue, profit and orders")
    df = load_table("gold_territory_summary")

    if df.empty:
        st.warning("gold_territory_summary returned no rows.")
        return

    col1, col2 = st.columns(2)
    with col1:
        section_label("Revenue by region")
        fig = px.bar(df.sort_values(COL["territory_revenue"], ascending=False), x=COL["territory"], y=COL["territory_revenue"])
        fig.update_traces(marker_color=CHART_COLORWAY[0])
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with col2:
        section_label("Profit by region")
        if COL["territory_profit"] in df.columns:
            fig = px.bar(df.sort_values(COL["territory_profit"], ascending=False), x=COL["territory"], y=COL["territory_profit"])
            fig.update_traces(marker_color=CHART_COLORWAY[1])
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("No profit column found for territories.")

    if COL["territory_orders"] in df.columns:
        section_label("Orders by region")
        fig = px.bar(df.sort_values(COL["territory_orders"], ascending=False), x=COL["territory"], y=COL["territory_orders"])
        fig.update_traces(marker_color=CHART_COLORWAY[4])
        st.plotly_chart(style_fig(fig), use_container_width=True)

    ranked = df.sort_values(COL["territory_revenue"], ascending=False)
    c1, c2 = st.columns(2)
    with c1:
        st.success(f"🏆 Best performing: **{ranked.iloc[0][COL['territory']]}**")
    with c2:
        st.error(f"⚠️ Worst performing: **{ranked.iloc[-1][COL['territory']]}**")

    with st.expander("Territory — full table"):
        st.dataframe(df, use_container_width=True)


def page_returns_analysis():
    page_header("↩️", "Returns analysis", "Where returns are concentrated, by product and category")
    df = load_table("gold_return_summary")

    if df.empty:
        st.warning("gold_return_summary returned no rows.")
        return

    col1, col2 = st.columns(2)
    with col1:
        section_label("Products with highest returns")
        top_returns = df.sort_values(COL["return_qty"], ascending=False).head(10)
        fig = px.bar(top_returns.sort_values(COL["return_qty"]), x=COL["return_qty"], y=COL["return_product"], orientation="h")
        fig.update_traces(marker_color=CHART_COLORWAY[3])
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with col2:
        if COL["return_category"] in df.columns:
            section_label("Category return performance")
            cat = df.groupby(COL["return_category"], as_index=False)[COL["return_qty"]].sum()
            fig = px.pie(cat, names=COL["return_category"], values=COL["return_qty"], hole=0.45)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("No category column found in gold_return_summary.")

    if COL["return_rate"] in df.columns:
        high_return = df[df[COL["return_rate"]] >= df[COL["return_rate"]].mean() + df[COL["return_rate"]].std()]
        if not high_return.empty:
            section_label("🚨 Return alerts — unusually high return rates")
            st.dataframe(high_return.sort_values(COL["return_rate"], ascending=False), use_container_width=True)

    with st.expander("Returns — full table"):
        st.dataframe(df, use_container_width=True)


def page_churn_prediction():
    page_header("🔮", "Churn prediction", "Active vs. churned customers and who's at risk")
    df = load_table("gold_customer_churn")

    if df.empty:
        st.warning("gold_customer_churn returned no rows.")
        return

    status_col = COL["churn_status"]
    if status_col in df.columns:
        churned = df[df[status_col].astype(str).str.lower().str.contains("churn")]
        active = df[~df.index.isin(churned.index)]
    else:
        churned, active = pd.DataFrame(), df

    total_customers = len(df)
    churn_count = len(churned)
    active_count = len(active)
    churn_rate = (churn_count / total_customers * 100) if total_customers else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Active Customers", fmt_number(active_count), icon="✅", accent="#0EA5A6", accent_soft="#ECFEFF")
    with c2:
        kpi_card("Churned Customers", fmt_number(churn_count), icon="⚠️", accent="#EF4444", accent_soft="#FEF2F2")
    with c3:
        kpi_card("Churn Rate", fmt_percent(churn_rate), icon="📉", accent="#F59E0B", accent_soft="#FFFBEB")

    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        section_label("Active vs churned")
        fig = go.Figure(data=[go.Pie(
            labels=["Active", "Churned"], values=[active_count, churn_count], hole=0.55,
            marker=dict(colors=[CHART_COLORWAY[1], CHART_COLORWAY[3]]),
        )])
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with col2:
        if COL["churn_recency"] in df.columns:
            section_label("Recency distribution (days since last purchase)")
            fig = px.histogram(df, x=COL["churn_recency"], nbins=30, color=status_col if status_col in df.columns else None)
            st.plotly_chart(style_fig(fig), use_container_width=True)

    section_label("Churn-risk customers")
    status_options = ["All"] + (sorted(df[status_col].dropna().unique().tolist()) if status_col in df.columns else [])
    chosen = st.selectbox("Filter by churn status", status_options, label_visibility="collapsed")
    filtered = df if chosen == "All" or status_col not in df.columns else df[df[status_col] == chosen]

    if COL["churn_recency"] in filtered.columns:
        filtered = filtered.sort_values(COL["churn_recency"], ascending=False)

    st.dataframe(filtered, use_container_width=True)


# ==========================================================================
# 5b. METRICS COLLECTION (Cached)
# ==========================================================================

@st.cache_data(ttl=REFRESH_TTL_SECONDS, show_spinner="Gathering metrics from Databricks…")
def gather_aggregated_metrics() -> dict:
    kpi_df = load_table("gold_kpi")
    monthly_df = load_table("gold_monthly_revenue")
    category_df = load_table("gold_category_summary")
    territory_df = load_table("gold_territory_summary")
    return_df = load_table("gold_return_summary")
    churn_df = load_table("gold_customer_churn")
    product_df = load_table("gold_product_summary")

    total_revenue = safe_first(kpi_df, "kpi_revenue") if not kpi_df.empty else safe_sum(monthly_df, "month_revenue")
    total_profit = safe_first(kpi_df, "kpi_profit") if not kpi_df.empty else safe_sum(monthly_df, "month_profit")
    total_orders = safe_first(kpi_df, "kpi_orders")
    total_customers = safe_first(kpi_df, "kpi_customers")

    revenue_trend_pct = None
    profit_trend_pct = None
    if not monthly_df.empty and COL["month"] in monthly_df.columns:
        m = sorted_monthly(monthly_df)
        if len(m) >= 2:
            prev_rev, last_rev = m[COL["month_revenue"]].iloc[-2], m[COL["month_revenue"]].iloc[-1]
            if prev_rev:
                revenue_trend_pct = (last_rev - prev_rev) / prev_rev * 100
            if COL["month_profit"] in m.columns:
                prev_p, last_p = m[COL["month_profit"]].iloc[-2], m[COL["month_profit"]].iloc[-1]
                if prev_p:
                    profit_trend_pct = (last_p - prev_p) / prev_p * 100

    top_categories = []
    if not category_df.empty:
        top_categories = (
            category_df.sort_values(COL["category_revenue"], ascending=False)
            .head(5)[[COL["category"], COL["category_revenue"]]]
            .to_dict("records")
        )

    territory_perf = []
    worst_territory = None
    if not territory_df.empty:
        t_sorted = territory_df.sort_values(COL["territory_revenue"], ascending=False)
        territory_perf = t_sorted[[COL["territory"], COL["territory_revenue"]]].to_dict("records")
        worst_territory = t_sorted.iloc[-1][COL["territory"]]

    avg_return_rate = None
    top_returned_products = []
    if not return_df.empty:
        if COL["return_rate"] in return_df.columns:
            avg_return_rate = float(return_df[COL["return_rate"]].mean())
        top_returned_products = (
            return_df.sort_values(COL["return_qty"], ascending=False)
            .head(5)[[COL["return_product"], COL["return_qty"]]]
            .to_dict("records")
        )

    churn_rate, churned_count, high_recency_customers = None, None, None
    if not churn_df.empty:
        status_col = COL["churn_status"]
        if status_col in churn_df.columns:
            churned = churn_df[churn_df[status_col].astype(str).str.lower().str.contains("churn")]
            churned_count = len(churned)
            churn_rate = churned_count / len(churn_df) * 100 if len(churn_df) else 0
        if COL["churn_recency"] in churn_df.columns:
            threshold = churn_df[COL["churn_recency"]].quantile(0.9)
            high_recency_customers = int((churn_df[COL["churn_recency"]] >= threshold).sum())

    top_products = []
    if not product_df.empty:
        top_products = (
            product_df.sort_values(COL["product_revenue"], ascending=False)
            .head(5)[[COL["product_name"], COL["product_revenue"]]]
            .to_dict("records")
        )

    return {
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "revenue_trend_pct": revenue_trend_pct,
        "profit_trend_pct": profit_trend_pct,
        "top_categories": top_categories,
        "territory_performance": territory_perf,
        "worst_territory": worst_territory,
        "avg_return_rate": avg_return_rate,
        "top_returned_products": top_returned_products,
        "churn_rate": churn_rate,
        "churned_customers": churned_count,
        "high_recency_customers": high_recency_customers,
        "top_products": top_products,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


SYSTEM_PROMPT = """You are a Business Intelligence Analyst.
Analyze the supplied business metrics and provide practical, data-driven recommendations.
Structure your analysis with:
## Executive Summary
3-5 key observations.
## Positive Trends
Important opportunities.
## Risks & Alerts
Important business risks.
## Customer Insights
Customer behavior and churn observations.
## Recommended Actions
Top 5 practical management actions.
Rules:
- Never invent numbers. Use only supplied metrics.
- Use actual numbers whenever available."""

# Automatic fallback chain across active Gemini models
AVAILABLE_MODELS = [
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
]


def call_gemini_stream(system_prompt: str, user_message: str, history: list = None):
    """Streams response tokens with automatic fallback if a model hits rate limits."""
    import google.generativeai as genai

    genai.configure(api_key=get_secret("GEMINI_API_KEY", required=True))
    last_err = None

    for m_name in AVAILABLE_MODELS:
        try:
            model = genai.GenerativeModel(model_name=m_name, system_instruction=system_prompt)
            if history:
                chat = model.start_chat(history=[
                    {"role": h["role"], "parts": [h["text"]]} for h in history
                ])
                response = chat.send_message(user_message, stream=True)
            else:
                response = model.generate_content(user_message, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as err:
            last_err = err
            err_str = str(err).lower()
            # If rate limit (429) or not found (404), seamlessly try next model
            if "429" in err_str or "quota" in err_str or "404" in err_str or "not found" in err_str:
                continue
            raise err

    raise last_err


def page_ai_insights():
    page_header("🤖", "AI business insights", "Powered by Google Gemini — analysis runs on aggregated KPIs, never raw customer-level data")

    if st.button("Generate AI Insights", type="primary"):
        try:
            metrics = gather_aggregated_metrics()
            user_message = f"Here are the aggregated business metrics (JSON):\n{metrics}"
            st.markdown("### 🤖 AI Business Insights")
            insight_text = st.write_stream(call_gemini_stream(SYSTEM_PROMPT, user_message))
            st.session_state["ai_insights"] = insight_text
            st.session_state["ai_insights_metrics"] = metrics
        except KeyError:
            st.error("GEMINI_API_KEY is missing from your Streamlit secrets.")
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                st.warning("⏳ Free-tier quota limit reached. Please wait ~30 seconds and click again.")
            else:
                st.error(f"Could not generate AI insights right now.\n\nDetails: {e}")

    elif "ai_insights" in st.session_state:
        st.markdown("### 🤖 AI Business Insights")
        st.markdown(st.session_state["ai_insights"])

        with st.expander("Rule-based alerts (computed locally, not by Gemini)"):
            m = st.session_state.get("ai_insights_metrics", {})
            render_alerts(compute_alerts(m))

        with st.expander("Raw aggregated metrics sent to Gemini"):
            st.json(st.session_state.get("ai_insights_metrics", {}))
    else:
        st.info("Click **Generate AI Insights** to run the analysis.")


CHAT_SYSTEM_PROMPT = """You are a helpful Business Intelligence assistant embedded in
Customer & Revenue Intelligence Platform.
Aggregated business metrics snapshot:
{metrics}
"""


def page_ai_chat():
    page_header("💬", "AI chat", "Ask questions about your business metrics — powered by Google Gemini")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if st.button("🔄 Reset conversation"):
        st.session_state["chat_history"] = []
        st.rerun()

    for turn in st.session_state["chat_history"]:
        with st.chat_message("user" if turn["role"] == "user" else "assistant"):
            st.markdown(turn["text"])

    prompt = st.chat_input("Ask about revenue, churn, top products, territories…")
    if prompt:
        st.session_state["chat_history"].append({"role": "user", "text": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                metrics = gather_aggregated_metrics()
                system_prompt = CHAT_SYSTEM_PROMPT.format(metrics=metrics)
                reply = st.write_stream(
                    call_gemini_stream(
                        system_prompt,
                        prompt,
                        history=st.session_state["chat_history"][:-1],
                    )
                )
            except Exception as e:
                reply = f"⚠️ Could not get a response right now.\n\nDetails: {e}"
                st.markdown(reply)
        st.session_state["chat_history"].append({"role": "model", "text": reply})


# ==========================================================================
# 6. LOGIN
# ==========================================================================

def login_page():
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] > .main {{
            background: linear-gradient(135deg, #1DD3B0 0%, #6C63FF 55%, #FF6B9D 100%);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown('<div class="login-title">Revenue Intelligence</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-sub">Sign in to view your dashboards</div>', unsafe_allow_html=True)

            with st.form("login_form", border=False):
                username = st.text_input("Username", placeholder="Username")
                password = st.text_input("Password", type="password", placeholder="Password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

            if submitted:
                valid_user = get_secret("APP_USERNAME", "admin")
                valid_pass = get_secret("APP_PASSWORD", "admin123")
                if username == valid_user and password == valid_pass:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")


# ==========================================================================
# 6b. HOME, REPORTS & SETTINGS
# ==========================================================================

def page_home():
    page_header("🏠", "Home", "Quick summary and shortcuts to every section")

    kpi_df = load_table("gold_kpi")
    total_revenue = safe_first(kpi_df, "kpi_revenue")
    total_profit = safe_first(kpi_df, "kpi_profit")
    total_orders = safe_first(kpi_df, "kpi_orders")
    total_customers = safe_first(kpi_df, "kpi_customers")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Revenue", fmt_currency(total_revenue), icon="💰", accent="#14B8A6")
    with c2:
        kpi_card("Total Profit", fmt_currency(total_profit), icon="📈", accent="#818CF8")
    with c3:
        kpi_card("Total Orders", fmt_number(total_orders), icon="🧾", accent="#F59E0B")
    with c4:
        kpi_card("Total Customers", fmt_number(total_customers), icon="👥", accent="#22D3EE")

    alerts = compute_alerts(gather_aggregated_metrics())
    if alerts:
        st.write("")
        section_label(f"⚠️ Active alerts ({len(alerts)})")
        render_alerts(alerts)

    st.write("")
    section_label("Jump to a section")

    tiles = [
        ("📈", "Executive Overview", "Company-wide revenue, profit and demand"),
        ("👥", "Customer Intelligence", "Top customers and revenue concentration"),
        ("📦", "Product Intelligence", "Best sellers by revenue, profit, volume"),
        ("🌍", "Territory Analysis", "Regional performance breakdown"),
        ("↩️", "Returns Analysis", "Where returns are concentrated"),
        ("🔮", "Churn Prediction", "Active vs. churned, who's at risk"),
        ("🤖", "AI Business Insights", "Gemini-generated analysis of your KPIs"),
        ("💬", "AI Chat", "Ask questions about your metrics"),
    ]
    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(tiles):
        with cols[i % 4]:
            st.markdown(
                f"""
                <div class="kpi-card" style="min-height:110px;">
                    <div class="kpi-icon">{icon}</div>
                    <div class="kpi-label" style="text-transform:none;font-size:0.85rem;margin-top:10px;">{title}</div>
                    <div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:4px;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def page_reports():
    page_header("📤", "Reports & export", "Preview any gold table and download it as CSV")

    table_key = st.selectbox("Choose a table", list(TABLES.keys()))
    df = load_table(table_key)

    if df.empty:
        st.warning(f"{table_key} returned no rows.")
        return

    c1, c2 = st.columns(2)
    with c1:
        kpi_card("Rows", fmt_number(len(df)), icon="📊", accent="#14B8A6")
    with c2:
        kpi_card("Columns", fmt_number(len(df.columns)), icon="🧮", accent="#818CF8")

    st.write("")
    section_label("Preview")
    st.dataframe(df.head(200), use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download full table as CSV",
        data=csv_bytes,
        file_name=f"{table_key}.csv",
        mime="text/csv",
        type="primary",
    )


def page_settings():
    page_header("⚙️", "Settings", "App configuration and cache controls")

    section_label("Connection")
    st.markdown(f"**Catalog:** `{CATALOG}`  \n**Schema:** `{SCHEMA}`")

    st.write("")
    section_label("Cache")
    st.markdown(f"Query results are cached for **{REFRESH_TTL_SECONDS // 60} minutes** before Databricks is queried again.")
    if st.button("🧹 Clear all cached data now", type="primary"):
        st.cache_data.clear()
        st.success("Cache cleared. Data will reload fresh on next page view.")

    st.write("")
    section_label("Column mapping")
    st.caption("If a chart looks empty or a page errors, edit the COL dictionary near top of app.py.")
    with st.expander("View current column mapping"):
        st.json(COL)


# ==========================================================================
# 7. SIDEBAR NAVIGATION
# ==========================================================================

NAV_GROUPS = [
    ("OVERVIEW", {
        "🏠  Home": page_home,
        "📈  Executive Overview": page_executive_overview,
    }),
    ("ANALYSIS", {
        "👥  Customer Intelligence": page_customer_intelligence,
        "📦  Product Intelligence": page_product_intelligence,
        "🌍  Territory Analysis": page_territory_analysis,
        "↩️  Returns Analysis": page_returns_analysis,
        "🔮  Churn Prediction": page_churn_prediction,
    }),
    ("AI TOOLS", {
        "🤖  AI Business Insights": page_ai_insights,
        "💬  AI Chat": page_ai_chat,
    }),
    ("MORE", {
        "📤  Reports & Export": page_reports,
        "⚙️  Settings": page_settings,
    }),
]

PAGES = {label: fn for _, group in NAV_GROUPS for label, fn in group.items()}


def main():
    if not st.session_state.get("authenticated", False):
        login_page()
        return

    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div>
                <div class="name">Revenue Intelligence</div>
                <div class="tagline">Customer & Revenue Platform</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    choice = st.session_state.get("current_page", "🏠  Home")
    if choice not in PAGES:
        choice = "🏠  Home"

    for group_name, group_pages in NAV_GROUPS:
        st.sidebar.markdown(
            f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.06em;'
            f'color:{TEXT_MUTED};margin:14px 0 4px 4px;">{group_name}</div>',
            unsafe_allow_html=True,
        )
        for label in group_pages:
            is_active = label == choice
            if st.sidebar.button(
                label,
                key=f"nav_{label}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["current_page"] = label
                st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if st.sidebar.button("🚪 Log out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state.pop("username", None)
        st.rerun()
    st.sidebar.caption(f"Cache TTL: {REFRESH_TTL_SECONDS // 60} min · Last loaded: {datetime.now().strftime('%H:%M:%S')}")

    st.sidebar.markdown(
        f"""
        <div class="sidebar-profile">
            <div class="dot"></div>
            <div>
                <div class="who">{st.session_state.get('username', 'User')}</div>
                <div class="role">Signed in</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    PAGES[choice]()


if __name__ == "__main__":
    main()