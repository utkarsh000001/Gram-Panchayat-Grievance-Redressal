# Gram Panchayat Grievance Redressal — Streamlit Prototype

A Python/Streamlit rebuild of the citizen chatbot + admin register (PS-24 MVP).

## Files
```
streamlit_app/
├── app.py                   # the whole application
├── requirements.txt         # streamlit, pandas
├── .streamlit/config.toml   # theme colors
└── README.md
```
Grievances are stored in a local SQLite file (`grievances.db`), created
automatically on first run in the same folder as `app.py`.

## Run it locally
```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```
It opens at `http://localhost:8501`. The "Citizen Portal" and "Panchayat
Admin" tabs share the same SQLite file, so anything filed on one side shows
up on the other immediately.

## Deploy to Streamlit Community Cloud (free)
Streamlit Cloud deploys from a GitHub repo — there's no CLI deploy step.

1. **Push this folder to GitHub**
   ```bash
   cd streamlit_app
   git init
   git add .
   git commit -m "Gram Panchayat grievance chatbot prototype"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. Click **"New app"**, pick your repo/branch, and set:
   - **Main file path:** `app.py`
4. Click **Deploy**. You'll get a URL like
   `https://<your-app>.streamlit.app`.

That's it — no Dockerfile, no server config needed for this MVP.

### Note on the database on Streamlit Cloud
Streamlit Cloud's filesystem is **ephemeral** — `grievances.db` resets
whenever the app restarts or redeploys (e.g. after a sleep/wake cycle or a
new push). That's fine for demoing the prototype, but for a real pilot
you'd point `DB_PATH` in `app.py` at a hosted database instead (e.g.
Postgres on Supabase/Neon, or SQLite via Turso) — a one-line change since
all the SQL is isolated in the `get_conn()` / query functions at the top
of `app.py`.

## Alternative: Streamlit Community Cloud via GitHub Desktop
If you'd rather not use the git CLI, GitHub Desktop → "Add local
repository" → point it at this folder → publish → then follow steps 2–4
above.
