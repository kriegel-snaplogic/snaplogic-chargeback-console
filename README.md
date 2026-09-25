# SnapLogic Chargeback Console

A Streamlit app that turns SnapLogic platform usage into a per-business-unit cost
breakdown — the thing finance asks for when a shared integration platform is paid
for centrally but used by everyone.

It attributes pipeline executions to business units, spreads Snaplex node cost and
platform overhead across them, and produces a monthly chargeback report you can
hand over.

> Ships with a synthetic demo dataset, so you can clone it and see the whole thing
> working before pointing it at your own org. See [Demo data](#demo-data).

## Screens

| Page | What it does |
|---|---|
| **Dashboard** | Cost per BU per month, execution volume, Snaplex utilisation, failure rates |
| **BU Management** | Define business units, cost centres, owners and headcount |
| **Asset Mapping** | Attribute users and project spaces to BUs, by user, project path or email domain |
| **Cost Configuration** | Node costs, licence and CoE overhead, allocation key (headcount / usage / blended) |
| **Reports** | Monthly chargeback report, export, ad-hoc re-ingest of a date range |

## Quick start

```bash
git clone https://github.com/kriegel-snaplogic/snaplogic-chargeback-console.git
cd snaplogic-chargeback-console
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

That runs on the bundled demo data — no credentials, no configuration.

## Connecting your own org

```bash
cp .env.example .env    # then fill it in
```

Two ways to get execution data in:

**1. Platform API (simplest).** Set `SNAPLOGIC_SERVER`, `SNAPLOGIC_ORG` and either
`SNAPLOGIC_USER` + `SNAPLOGIC_PASSWORD` or `SNAPLOGIC_TOKEN`. The console reads
runtime executions, project paths and the org user list directly. Good to a few
weeks of history, which is as far back as the Public API goes.

**2. Snowflake-backed history (for longer retention).** A scheduled SnapLogic
pipeline lands executions in a Snowflake table and the console reads them back
through a triggered task. Set `SNAPLOGIC_USE_SNOWFLAKE=true` plus the
`SL_READ_*` / `SL_INGEST_*` / `SL_ADHOC_*` pairs. See `snowflake_client.py` for
the expected task contract and response shapes.

Neither is required. With neither configured the app stays on the fixtures.

### Admin access

The admin pages sit behind Google OAuth with a PIN fallback. Both come from
`.streamlit/secrets.toml` — see the block at the end of `.env.example`. Set
`allowed_email_domain` to restrict sign-in to your own domain if you deploy this
anywhere reachable.

## How attribution works

An execution is attributed to a BU by the first rule that matches:

1. **User mapping** — exact match on the executing user's email.
2. **Email domain rule** — everyone at a domain to one BU. Useful for partners
   and contractors.
3. **Project path prefix** — longest matching `/<org>/<space>` prefix. This is the
   fallback that matters in practice, because triggered and scheduled runs often
   carry no requesting user.
4. Anything left over lands in **Other / External**.

Users on the excluded list (training accounts, bots, leavers) are dropped before
allocation rather than charged to anyone.

Cost then comes from three inputs, all editable in Cost Configuration:

- **Snaplex node cost** — nodes × monthly cost per node, split across the BUs
  that used that Snaplex, weighted by execution time.
- **Platform overhead** — licence, CoE opex, cloud infra.
- **Allocation key** — headcount, usage, or a blend (default 70% headcount).

Per-execution duration is capped at 60 minutes, because always-on listener
pipelines otherwise swamp everything else.

## Demo data

The bundled fixtures — `user_state.json`, `data/platform_users.csv` and
`exec_data_computed.json` — are **synthetic**. They were derived from a real org
export by replacing every identity, but the shape was kept: ~1,000 users, the
internal/external split, per-company clustering of external users, group
memberships, role mix, and a plausible spread of cost across BUs.

Specifically:

- Email addresses are `first.last@snaplogic.com` for internal users and
  `first.last@ext-<hash>.com` for external ones. The `ext-` hash is stable per
  original company, so "everyone from one partner" still clusters — but the
  company is not recoverable from it.
- Display names come from a gender-neutral pool and imply nothing about the
  person they replaced.
- Project spaces, customer project names and business-unit owners are
  placeholders.
- Execution counts and durations in `exec_data_computed.json` are aggregates
  only — no pipeline names, paths or users.

None of it refers to a real person, customer or partner. Node costs and overhead
figures are illustrative placeholders; replace them with your own contracted
rates before reading anything into the numbers.

## Repo layout

```
app.py                     Entry point, connection setup, session bootstrap
theme.py                   Branding, nav, admin gate (OAuth + PIN)
api_client.py              SnapLogic Public API client and BU attribution
snowflake_client.py        Triggered-task client for Snowflake-backed history
mock_data.py               Demo fixtures, cost engine, session state
pages/                     The five Streamlit pages
data/platform_users.csv    Synthetic org user list, auto-loaded on startup
user_state.json            Synthetic BU assignments and project tree
exec_data_computed.json    Pre-aggregated execution data (fast startup)
```

## Caveats

- Single-process by design. Session state is in-memory and the background
  refresh assumes one worker; it is a console for a small team, not a
  multi-tenant service.
- Edits made in the UI persist to `user_state.json` next to the code, so a
  container restart loses them unless that path is on a volume.
- `user_mappings` allows the same user in more than one BU. Where that happens
  the last one wins. Worth tidying in Asset Mapping if your numbers look off.

## Licence

MIT — see [LICENSE](LICENSE).
