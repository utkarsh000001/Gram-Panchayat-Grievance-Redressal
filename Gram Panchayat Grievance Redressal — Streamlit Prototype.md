# Gram Panchayat Grievance Redressal — Streamlit Prototype

A Python/Streamlit rebuild of the citizen chatbot + admin register (PS-24 MVP).

## Files
```
streamlit_app/
├── app.py                   # the whole application
├── requirements.txt         # Streamlit, pandas, speech recognition, boto3
├── .streamlit/config.toml   # theme colors
├── .streamlit/secrets.toml.example  # Admin credential template
└── README.md
```
Grievances are stored in a local SQLite file (`grievances.db`), created
automatically on first run in the same folder as `app.py`.

### What's new
- **Protected Admin area**: the Citizen Portal remains public, while the Panchayat Admin dashboard requires an Admin ID and password. Credentials are read from Streamlit secrets or environment variables and are not stored in the database.
- **Speech-to-text input**: citizens can record their complaint from supported browsers and transcribe it into the chatbot using Google Speech Recognition; typed input remains available as a fallback.
- **Downloadable complaint slip**: after filing, citizens can download a plain-text slip containing the exact `GP/YYYY/NNNN` tracking ID and complaint details.
- **Refreshable live tracker**: tracking results include a refresh control that re-reads the latest status from SQLite.
- **Optional S3 photo storage**: when `S3_BUCKET` and AWS credentials are configured, uploaded photos are stored in S3 and the Admin preview uses a presigned URL. Without S3 configuration, the local SQLite demo fallback is used.
- **Escalation flags**: Admin tab shows an adjustable "overdue after N days"
  threshold; open grievances past it get a ⚠️ flag and an "Overdue only"
  filter, plus an "Age (days)" column.
- **Photo upload**: citizens can optionally attach a photo when filing;
  it's stored in SQLite and shown as a thumbnail in the Admin register.
- **Bilingual citizen flow**: the whole chatbot (prompts, buttons, the
  complaint slip, status timeline) runs in English or हिन्दी based on the
  citizen's choice at the start. The Admin tab stays English (staff-facing).

## Run it locally
```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```
It opens at `http://localhost:8501`. The Citizen Portal is available without login. The Panchayat Admin tab displays only an ID/password login until valid credentials are entered. Both views share the same SQLite file, so anything filed on the Citizen side appears in the Admin register immediately.

### Configure the Admin login

For local development, copy the template and set a strong password:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:
```toml
ADMIN_ID = "your-admin-id"
ADMIN_PASSWORD = "your-strong-password"
```

The default fallback login is `admin` / `change-me` only when no secrets or environment variables are configured. Change it before sharing or deploying the app. The app also accepts `ADMIN_ID` and `ADMIN_PASSWORD` environment variables.

For optional S3 photo storage, configure `S3_BUCKET`, `AWS_REGION`, and standard AWS credentials such as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. If those values are absent, the prototype stores photo bytes locally in SQLite for demonstration purposes only.

The Admin session is protected for the current browser session and includes a **Log out** button. This is suitable for the prototype; a production deployment should use a proper identity provider, hashed/password-managed credentials, HTTPS, and a persistent server-side database.

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
4. In **Advanced settings → Secrets**, paste the contents of your configured `secrets.toml` file, for example:
   ```toml
   ADMIN_ID = "your-admin-id"
   ADMIN_PASSWORD = "your-strong-password"
   ```
5. If using S3 photo storage, also add the S3 bucket and AWS credential variables in the deployment’s secrets/environment settings.
6. Click **Deploy**. You'll get a URL like
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
