# Streamlit deployment fix
This package is the Streamlit-compatible dashboard build.

Deploy on Streamlit Community Cloud with:
- Repository: your `hadar-live-trading-bot` repo
- Branch: `main`
- Main file: `app.py`

Important: this dashboard scans while the app is active. For true 24/7 background alerts/webhooks, the original FastAPI service should be deployed to an always-on service (Render/Railway/Fly/etc.) separately.
