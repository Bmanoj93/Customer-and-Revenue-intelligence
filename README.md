# Customer & Revenue Intelligence Platform — Setup Guide

## Step 1 — Create project folder
Create a folder anywhere on your computer, e.g. `customer_revenue_platform`, and put the three files below inside it (keeping the `.streamlit` subfolder).

```
customer_revenue_platform/
├── app.py
├── requirements.txt
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

## Step 2 — app.py
Already provided — just save it as `app.py` in the project folder.

## Step 3 — requirements.txt
Already provided — save it as `requirements.txt` in the project folder.

## Step 4 — Create `.streamlit/secrets.toml`
Inside the `.streamlit` folder, **copy** `secrets.toml.example` to a new file named `secrets.toml` (same folder). This is the real file the app reads — never commit it to git or share it.

## Step 5 — Add Databricks credentials
Open `secrets.toml` and fill in:

- `DATABRICKS_SERVER_HOSTNAME`
- `DATABRICKS_HTTP_PATH`
- `DATABRICKS_TOKEN`

Where to find them, in Databricks:
1. Go to **SQL Warehouses** in your Databricks workspace sidebar.
2. Click your SQL Warehouse (create one if needed — a Serverless or Small warehouse is fine for a capstone).
3. Open the **Connection Details** tab. It shows the **Server hostname** and **HTTP path** — copy both exactly.
4. For the token: click your **user profile icon (top right) → Settings → Developer → Access tokens → Generate new token**. Copy it immediately (it's shown only once) and paste it into `DATABRICKS_TOKEN`.

## Step 6 — Add your free Google Gemini API key
1. Go to https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Create API key** (no credit card required — this is the free tier).
3. Copy the key (starts with `AIzaSy`) and paste it into `GEMINI_API_KEY` in `secrets.toml`.

## Step 6b — Set your login credentials
The app now opens on a login screen before showing any dashboard. Set `APP_USERNAME` and `APP_PASSWORD` in `secrets.toml` to whatever you want. If you leave them out, it falls back to `admin` / `admin123` — fine for testing, but change it before sharing the app with anyone else.

## Step 7 — Install requirements
Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

(Use a virtual environment if you prefer: `python -m venv venv` then activate it before installing.)

## Step 8 — Run Streamlit

```bash
streamlit run app.py
```

Your browser should open automatically at `http://localhost:8501`.

## Step 9 — Verify each dashboard page
Use the sidebar to click through: Executive Overview, Customer Intelligence, Product Intelligence, Territory Analysis, Returns Analysis, and Churn Prediction. Each page queries your Databricks Gold tables live — if a chart is empty, check that the corresponding gold table has data and that the column names match the `COL` dictionary near the top of `app.py` (edit that dictionary if your column names differ).

## Step 10 — Test AI Business Insights
Go to the **AI Business Insights** page and click **Generate AI Insights**. Gemini receives only the aggregated KPIs (never raw customer rows) and returns a structured business analysis.

## Step 11 — Try the AI Chat page
Go to the **AI Chat** page and ask a question like "which category has the highest revenue?" or "how many customers have churned?". Gemini answers using the same aggregated KPI snapshot, with the conversation kept in a normal chat thread. Click **🔄 Reset conversation** to start over.

## What's new: Home, Reports, and Settings
The sidebar is now grouped into **OVERVIEW**, **ANALYSIS**, **AI TOOLS**, and **MORE**:
- **🏠 Home** — top-level KPIs, active alerts, and a tile grid linking to every section.
- **📤 Reports & Export** — pick any gold table, preview it, and download it as a CSV.
- **⚙️ Settings** — see the catalog/schema in use, clear the cache on demand, and view the current `COL` column-mapping as a quick reference.

---

### Notes
- All secrets are read from `st.secrets` — nothing is hardcoded in `app.py`.
- **No `secrets.toml` yet?** The login screen still works — it falls back to `admin` / `admin123` when `APP_USERNAME`/`APP_PASSWORD` aren't set. But the Databricks and Claude pages will show a clear on-screen message (not a crash) telling you exactly which secret is missing and where to add it.
- Query results are cached for 10 minutes (`REFRESH_TTL_SECONDS` in `app.py`) to avoid hammering the warehouse; use the **🔄 Refresh data** button in the sidebar to force a reload.
- If a page shows "no rows" or a column warning, double-check the table/column names against the `TABLES` and `COL` dictionaries at the top of `app.py`.
- The dark theme comes from two places that need to stay in sync if you re-theme: the color constants near the top of `app.py` (`ACCENT`, `BG_DARK`, `CARD_DARK`, etc.) and `.streamlit/config.toml`, which sets Streamlit's native theme (buttons, inputs, dataframes). Change both together.
