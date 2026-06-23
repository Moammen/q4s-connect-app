# q4s-connect-app

Monorepo for the Q4S / ETS (Energy Transfer Station) platform.

## Projects

- **`q4s_connect/`** — Main Django + DRF backend for ETS monitoring and billing
  of district-cooling chilled-water systems. Collects BTU-meter telemetry over
  OPC UA, stores live and historical readings, runs alarm rules and Celery-based
  polling, and manages monthly delta-T / consumption billing.
- **`q4s_site_monitoring/`** — Companion service for shareable, password-protected
  external site-dashboard links.

## Notes

- Secrets (the `Cloud/` folder, `.env`, credential files) are gitignored and must
  not be committed.
- Each project has its own virtual environment (`venv/` / `.venv/`), also ignored.
