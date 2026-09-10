# Kinday (frontend prototype)

A Next.js calendar UI mocking what a parent-facing view of the Family Activity
Deep Agent's weekly plan could look like. This is a **visual prototype, not a
client of the backend**:

- All data (family members, activities, school events) is hardcoded in
  [app/page.tsx](app/page.tsx) and persisted only to the browser's
  `localStorage`. It seeds from the same demo month the backend's
  `tools/seed_month_demo.py` generates, but the two are not connected.
- It does not call the MCP server or read `data/family_activity.db`. Nothing
  you do here writes back to the agent's calendar, and nothing the agent does
  updates this UI.
- There is no auth, no API layer, and no server-side persistence.

It exists to answer "what would this look like for a parent," not as a
production frontend. Wiring it to the real backend (an API layer over the MCP
tools, replacing the in-browser mock state with live reads/writes) is future
work.

## Run it locally

    cd frontend
    npm install
    npm run dev

This starts a local dev server (see the console output for the port). Build
output (`.next/`, `dist/`, etc.) and `node_modules/` are gitignored and
regenerate from `npm install` / `npm run build`.
