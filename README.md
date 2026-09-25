# SnapLogic Chargeback Console

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://snaplogic-chargeback-console.streamlit.app/)

**Live demo → [snaplogic-chargeback-console.streamlit.app](https://snaplogic-chargeback-console.streamlit.app/)**

A Streamlit app that turns SnapLogic platform usage into a per-business-unit cost
breakdown — the thing finance asks for when a shared integration platform is paid
for centrally but used by everyone.

It attributes pipeline executions to business units, spreads Snaplex node cost and
platform overhead across them, and produces a monthly chargeback report you can
hand over.

> The live demo and this repo both run on a synthetic dataset — see
> [Demo data](#demo-data). The demo is public and has no login, so treat anything
> you change in it as visible to the next visitor; see
> [Access control](#access-control--there-is-none-right-now).

## Screens

| Page | What it does |
|---|---|
| **Dashboard** | 7-month cost trend, cost by category and by BU, execution volume and error rate, node runtime per BU |
| **BU Management** | Define business units, cost centres, owners and headcount |
| **Asset Mapping** | Attribute users and project spaces to BUs, by user, project path or email domain |
| **Cost Configuration** | Node count and cost per Snaplex, licence / CoE / infra overhead, per-execution startup overhead, allocation key |
| **Reports** | Per-BU chargeback invoice, 3-month cost projection, CSV export, and triggering a data ingest |

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
runtime executions, project paths and the org user list directly, querying a
month at a time with pagination. How far back you can go is whatever your org's
runtime log retention allows.

**2. Snowflake-backed history (for longer retention).** A scheduled SnapLogic
pipeline lands executions in a Snowflake table and the console reads them back
through a triggered task. Set `SNAPLOGIC_USE_SNOWFLAKE=true` plus the
`SL_READ_*` / `SL_INGEST_*` / `SL_ADHOC_*` pairs. See `snowflake_client.py` for
the expected task contract and response shapes.

Neither is required. With neither configured the app stays on the fixtures.

### Access control — there is none right now

**Every page is open. There is no authentication.** `theme.py` contains a working
admin gate (`require_admin`, Google OAuth with a PIN fallback), but nothing calls
it — it has zero call sites. The gate was removed from Asset Mapping and Cost
Configuration and never reinstated anywhere else.

That is fine locally. It matters if you host this, because Asset Mapping and Cost
Configuration are editable, and the "add environment" form accepts real
credentials for a live org.

To turn it back on, call `require_admin(st)` at the top of the pages you want
protected and set these in `.streamlit/secrets.toml`:

```toml
demo_pin = "your-pin"
allowed_email_domain = "yourcompany.com"   # optional; unset means any Google account
```

Related: UI edits call `save_user_state()`, which writes `user_state.json` next to
the code. On a hosted single-container deployment that file is shared by every
visitor, so one person's edits change what the next person sees until the
container recycles. Point `_STATE_PATH` somewhere per-session, or treat a hosted
instance as read-only.

## How attribution works

There are **two attribution paths**, and they do not behave identically. Which one
runs depends on where the execution data came from.

**Fixtures and Snowflake** — `rows_to_exec_data()` in `mock_data.py`. This is the
path the bundled demo uses. Attribution is by **project path only**:

1. Longest matching `/<org>/<space>` prefix from `project_mappings` wins
   (case-insensitive, longest prefix first).
2. Anything unmatched lands in **Other / External** (`bu_other`).

Note that `rows_to_exec_data()` takes a `user_mappings` argument and does not use
it. On this path, user-level mappings do not affect which BU an execution is
charged to — they only feed headcount (see below).

**Live Platform API** — `aggregate_by_snaplex_and_bu()` in `api_client.py`:

1. Executions by an **excluded user** are dropped before anything else.
2. **User mapping** — exact match on the executing `user_id`, and it takes
   priority over the project path.
3. **Project path prefix** — first match wins in `project_mappings` insertion
   order, *not* longest-prefix order.
4. Anything unmatched is **dropped from the report entirely**, not bucketed into
   Other / External.

So the same month of data can total differently depending on the source. If you
are comparing the two, that is why.

**Domain rules** (Asset Mapping → Domain Rules) are not a runtime attribution
rule. They are a bulk-assignment helper: "Apply domain rules to all unassigned
users" writes `user_mappings` entries for everyone at a matching domain. Useful
for putting all partner accounts in one BU in a couple of clicks.

### Cost

Snaplex cost, for Snaplexes with `env = Production` (unless you enable dev ones
in Cost Configuration):

- **Dedicated** — nodes × cost per node, charged **in full** to the owning BU.
- **Shared / Cloudplex** — nodes × cost per node, split across BUs by each BU's
  share of *adjusted execution minutes* on that specific Snaplex, where adjusted
  minutes add a per-execution startup overhead (10s by default) to actual
  runtime. That stops thousands of sub-second runs looking free next to a handful
  of long ones.

Platform overhead is licence + CoE opex + cloud infra, allocated separately by
the **allocation key**:

| Key | Basis |
|---|---|
| `equal` | Split evenly across all BUs |
| `usage_weighted` | Share of total execution minutes |
| `headcount` | Share of total headcount |
| `blended` | Weighted mix of the two — **shipped default, 70% headcount / 30% usage** |

Headcount is derived from the count of email-format `user_mappings` per BU when
mappings are present, and falls back to the manual `headcount` field on each BU
otherwise. This is the main way user mappings influence the numbers on the demo
path.

Per-execution duration is capped at 60 minutes (`_MAX_EXEC_SEC`), because
always-on listener pipelines would otherwise swamp everything else.

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
theme.py                   Branding, top nav, and require_admin() — currently unused
api_client.py              Public API client + live-path BU attribution
snowflake_client.py        Triggered-task client for Snowflake-backed history
mock_data.py               Demo fixtures, fixture-path attribution, cost engine,
                           session state
pages/                     The five Streamlit pages
data/platform_users.csv    Synthetic org user list, auto-loaded on startup
user_state.json            Synthetic BU assignments and project tree
exec_data_computed.json    Pre-aggregated execution data (fast startup)
```

## Known rough edges

Documented rather than hidden, because they change how you should read the
numbers:

- **The two attribution paths disagree.** Unmatched executions go to
  `bu_other` on the fixture/Snowflake path but are dropped entirely on the live
  API path, and prefix matching is longest-first on one and insertion-order on
  the other. Same data, different totals.
- **`rows_to_exec_data()` ignores its `user_mappings` argument.** On the demo
  path, user-level mappings do not move cost between BUs; only project paths
  and headcount do.
- **No access control.** `require_admin` exists and is never called — see
  [Access control](#access-control--there-is-none-right-now).
- **UI edits are global on a hosted instance.** `save_user_state()` writes to
  disk next to the code, shared across all visitors of one container, and is
  lost when it recycles.
- **A user can be mapped to more than one BU.** The bundled fixtures contain 8
  such users. The last mapping wins. Tidy them in Asset Mapping if a BU's
  headcount looks wrong.
- **Single-process by design.** Session state is in-memory and the background
  refresh assumes one worker. It is a console for a small team, not a
  multi-tenant service.

## Licence

MIT — see [LICENSE](LICENSE).
