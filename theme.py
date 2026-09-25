"""
SnapLogic brand theme — dark mode with SnapLogic accent colours.

Usage on every page (after set_page_config, after init_session_state):
    from theme import inject_brand
    inject_brand(st, active="Dashboard")
"""
import base64, os
import plotly.io as _pio
import plotly.graph_objects as _go

# ── Brand palette ─────────────────────────────────────────────────────────────
NAVY   = "#001934"   # top-nav background only
BLUE   = "#4073FF"   # primary accent / active highlight
JADE   = "#42A5D2"   # secondary / live-connection badge
ORANGE = "#FF7D3F"   # warning / demo badge

# Dark-mode UI tones  (config.toml owns the base; CSS fine-tunes)
_CARD   = "#1A2636"
_BORDER = "#2E3D52"
_TEXT   = "#E8EDF4"
_MUTED  = "#8A9BB5"

# ── Navigation items: (url_path, display_label) ───────────────────────────────
NAV_ITEMS = [
    ("",                    "Home"),
    ("Dashboard",           "Dashboard"),
    ("BU_Management",       "BU Management"),
    ("Asset_Mapping",       "Asset Mapping"),
    ("Cost_Configuration",  "Cost Config"),
    ("Reports",             "Reports"),
]

# ── Plotly brand template ─────────────────────────────────────────────────────
def _register_plotly_template():
    _pio.templates["snaplogic"] = _go.layout.Template(
        layout=_go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Helvetica Neue, Helvetica, Arial, sans-serif",
                color=_TEXT, size=12,
            ),
            title=dict(font=dict(color=_TEXT, size=14)),
            xaxis=dict(
                gridcolor=_BORDER, linecolor=_BORDER,
                tickcolor=_BORDER, zerolinecolor=_BORDER,
                tickfont=dict(color=_MUTED),
            ),
            yaxis=dict(
                gridcolor=_BORDER, linecolor=_BORDER,
                tickcolor=_BORDER, zerolinecolor=_BORDER,
                tickfont=dict(color=_MUTED),
            ),
            legend=dict(
                bgcolor="rgba(26,38,54,0.92)",
                bordercolor=_BORDER, borderwidth=1,
                font=dict(color=_TEXT),
            ),
            colorway=[BLUE, JADE, ORANGE, "#6366F1", "#10B981",
                      "#F59E0B", "#EC4899", "#8B5CF6", "#EF4444"],
        )
    )
    _pio.templates.default = "plotly+snaplogic"


# ── Logo helper ───────────────────────────────────────────────────────────────
def _b64(filename):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", filename)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── Admin gate — Google OAuth with PIN fallback ───────────────────────────────
import hashlib as _hashlib

_ADMIN_PARAM = "s"   # URL query param that carries the session token


def _pin_token(pin: str) -> str:
    """Derive a short URL-safe token from the PIN (not secret, just obfuscated)."""
    return _hashlib.sha256(f"sl-admin-{pin}".encode()).hexdigest()[:12]


def require_admin(st_obj, page_path=None):
    """Grant access via Google OAuth (if configured) or a demo PIN from secrets.

    Priority:
      1. Google OAuth → @snaplogic.com account
      2. URL query param ?s=<token> — set on PIN success and carried in nav links
      3. demo_pin in secrets → prompt once; on success the token is added to the URL
      4. No auth configured → open access (demo mode)

    Add to Streamlit secrets for PIN fallback:
      demo_pin = "your-pin-here"
    """
    # ── 1. Google OAuth path ───────────────────────────────────────────────────
    _oauth_ok = False
    try:
        _auth_cfg = st_obj.secrets.get("auth", {})
        _oauth_ok = bool(_auth_cfg.get("google", {}).get("client_id"))
    except Exception:
        pass

    # Restrict OAuth sign-in to one email domain. Set allowed_email_domain in
    # Streamlit secrets; unset means any Google account that completes sign-in
    # is accepted, so set it if the deployment is reachable publicly.
    try:
        _allowed_domain = st_obj.secrets.get("allowed_email_domain")
    except Exception:
        _allowed_domain = None

    if _oauth_ok:
        user = st_obj.user
        if user.is_logged_in:
            if _allowed_domain and not user.email.endswith(f"@{_allowed_domain}"):
                st_obj.error(f"Access restricted to @{_allowed_domain} accounts. "
                             f"**{user.email}** is not authorised.")
                if st_obj.button("Sign out", key="_google_logout_wrong"):
                    st_obj.logout()
                st_obj.stop()
                return
            _c1, _c2 = st_obj.columns([5, 1])
            _c1.caption(f"🔐 Signed in as **{user.email}**")
            if _c2.button("Sign out", key="_google_logout_btn"):
                st_obj.logout()
            return

    # ── Resolve PIN from secrets ───────────────────────────────────────────────
    _demo_pin = None
    try:
        _demo_pin = st_obj.secrets.get("demo_pin") or st_obj.secrets.get("DEMO_PIN")
    except Exception:
        pass

    # ── 2. URL token check (survives page navigation via nav links) ────────────
    if _demo_pin:
        _expected = _pin_token(str(_demo_pin))
        if st_obj.query_params.get(_ADMIN_PARAM) == _expected:
            st_obj.session_state["_admin_unlocked"] = True
            st_obj.session_state.setdefault("_admin_label", "SnapLogic Admin")

    # ── 3. Already unlocked this session ─────────────────────────────────────
    if st_obj.session_state.get("_admin_unlocked"):
        _pin_label = st_obj.session_state.get("_admin_label", "Demo mode")
        _c1, _c2 = st_obj.columns([5, 1])
        _c1.caption(f"🔓 {_pin_label}")
        if _c2.button("Lock", key="_lock_btn"):
            st_obj.session_state["_admin_unlocked"] = False
            try:
                del st_obj.query_params[_ADMIN_PARAM]
            except Exception:
                pass
            st_obj.rerun()
        return

    # ── 4. Show access gate ───────────────────────────────────────────────────
    st_obj.markdown("---")

    if _oauth_ok:
        st_obj.markdown(
            "### 🔒 Admin access required\n"
            "Sign in with your **SnapLogic Google account** to continue."
        )
        _col, _ = st_obj.columns([1, 3])
        with _col:
            if st_obj.button("Sign in with Google", type="primary", use_container_width=True, key="_google_login_btn"):
                st_obj.login("google")
    else:
        st_obj.markdown(
            "### 🔒 Configuration page\n"
            "Enter the access PIN to continue."
        )

    if _demo_pin:
        with st_obj.expander("🔑 Enter PIN" if _oauth_ok else "🔑 PIN required", expanded=not _oauth_ok):
            _entered = st_obj.text_input("Access PIN", type="password", key="_pin_input",
                                         placeholder="Enter PIN from Streamlit secrets")
            if st_obj.button("Unlock", key="_pin_submit"):
                if _entered == str(_demo_pin):
                    # Write token into URL — nav links will carry it automatically
                    st_obj.query_params[_ADMIN_PARAM] = _pin_token(str(_demo_pin))
                    st_obj.session_state["_admin_unlocked"] = True
                    st_obj.session_state["_admin_label"] = "SnapLogic Admin"
                    st_obj.rerun()
                else:
                    st_obj.error("Incorrect PIN.")
    elif not _oauth_ok:
        st_obj.session_state["_admin_unlocked"] = True
        st_obj.session_state["_admin_label"] = "Demo mode"
        st_obj.rerun()

    st_obj.stop()


# ── Main entry point ──────────────────────────────────────────────────────────
def inject_brand(st_obj, active="Home"):
    """Call once per page, after set_page_config() and init_session_state()."""
    from mock_data import active_environments
    _register_plotly_template()
    _envs = active_environments(st_obj)
    # Carry admin token through nav links so PIN survives page navigation
    _admin_tok = st_obj.query_params.get(_ADMIN_PARAM, "")
    _conn_env = _envs[0] if _envs else None
    # Fall back to Snowflake live badge when no API env is connected
    _data_source = st_obj.session_state.get("_exec_data_source")
    if not _conn_env and _data_source == "snowflake":
        _conn_env = {"name": "Snowflake"}
    _inject_css(st_obj)
    _render_topnav(st_obj, active, _conn_env, _admin_tok)


# ── CSS ───────────────────────────────────────────────────────────────────────
def _inject_css(st_obj):
    st_obj.markdown(f"""<style>
/* ── Dark background fires before any content renders ── */
html, body, .stApp {{
    background-color: {NAVY} !important;
}}

/* ── Page fade-in on every navigation ───── */
@keyframes sl-fadein {{
    from {{ opacity: 0; transform: translateY(5px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.main .block-container {{
    animation: sl-fadein 0.18s ease-out;
}}

/* ── Global font ─────────────────────────── */
html, body, [class*="css"] {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important;
}}

/* ── Hide Streamlit chrome ───────────────── */
header[data-testid="stHeader"]       {{ display: none !important; }}
#MainMenu                            {{ display: none !important; }}
footer                               {{ display: none !important; }}
[data-testid="stDeployButton"]       {{ display: none !important; }}
[data-testid="stSidebarNav"]         {{ display: none !important; }}
[data-testid="stSidebar"]            {{ display: none !important; }}
section[data-testid="stSidebar"]     {{ display: none !important; }}

/* ── Main content ────────────────────────── */
.main .block-container {{
    max-width: 1400px !important;
    padding-top: 1.25rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
}}

/* ── Top nav spacer ──────────────────────── */
.sl-nav-spacer {{ height: 68px; }}

/* ── Fixed top navigation bar ───────────── */
.sl-topnav {{
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 999999;
    height: 60px;
    background: {NAVY};
    border-bottom: 3px solid {BLUE};
    display: flex;
    align-items: center;
    padding: 0 2rem;
    gap: 0;
    box-shadow: 0 2px 20px rgba(0,0,0,0.5);
}}
.sl-topnav-logo {{
    height: 26px;
    margin-right: 2.5rem;
    flex-shrink: 0;
}}
.sl-topnav-links {{
    display: flex;
    align-items: center;
    gap: 2px;
    flex: 1;
}}
.sl-navlink {{
    color: rgba(255,255,255,0.62) !important;
    text-decoration: none !important;
    padding: 6px 13px;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    letter-spacing: 0.01em;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
}}
.sl-navlink:hover {{
    color: rgba(255,255,255,0.95) !important;
    background: rgba(255,255,255,0.10);
    text-decoration: none !important;
}}
.sl-navlink-active {{
    color: #ffffff !important;
    background: {BLUE} !important;
    font-weight: 600;
}}
.sl-navlink-active:hover {{
    background: #3060ee !important;
    color: #ffffff !important;
}}
.sl-topnav-badge {{
    flex-shrink: 0;
    margin-left: auto;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    border: 1px solid;
    white-space: nowrap;
}}
.sl-badge-live {{
    background: rgba(66,165,210,0.15);
    border-color: {JADE};
    color: {JADE};
}}
.sl-badge-demo {{
    background: rgba(255,125,63,0.15);
    border-color: {ORANGE};
    color: {ORANGE};
}}

/* ── Hide any stray page_links (not used for nav) ── */
[data-testid="stPageLink"] {{ display: none !important; }}

/* ── Headings ────────────────────────────── */
h1 {{ color: {_TEXT} !important; font-weight: 700; margin-bottom: 0.25rem; }}
h2 {{ color: {_TEXT} !important; font-weight: 600; }}
h3 {{ color: {_TEXT} !important; font-weight: 600; }}
h4 {{ color: {_TEXT} !important; font-weight: 600; }}

/* ── Page title accent bar ───────────────── */
.stApp h1:first-of-type {{
    font-size: 1.6rem !important;
    color: {_TEXT} !important;
    border-left: 4px solid {BLUE};
    padding-left: 0.75rem;
    margin-bottom: 0.5rem;
}}

/* ── Metrics ─────────────────────────────── */
[data-testid="stMetricValue"] {{
    color: {_TEXT} !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}}
[data-testid="stMetricLabel"] {{
    color: {_MUTED} !important;
    font-weight: 600 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
[data-testid="stMetricDelta"] {{ font-size: 0.8rem !important; }}

/* ── Metric cards ────────────────────────── */
[data-testid="stMetric"] {{
    background: {_CARD} !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.35) !important;
    border: 1px solid {_BORDER} !important;
    border-top: 3px solid {BLUE} !important;
}}

/* ── Buttons ─────────────────────────────── */
.stButton > button {{
    border-radius: 6px !important;
    font-weight: 600 !important;
}}

/* ── Tabs ────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 2px solid {_BORDER};
    background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
    color: {_MUTED} !important;
    font-weight: 500;
    padding: 8px 18px;
    background: transparent;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}}
.stTabs [aria-selected="true"] {{
    color: {BLUE} !important;
    border-bottom: 2px solid {BLUE} !important;
    font-weight: 700 !important;
    background: transparent !important;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: {_TEXT} !important;
    background: rgba(64,115,255,0.08) !important;
}}

/* ── Expanders ───────────────────────────── */
[data-testid="stExpander"] {{
    background: {_CARD} !important;
    border: 1px solid {_BORDER} !important;
    border-radius: 8px !important;
}}
[data-testid="stExpander"] > details > summary,
[data-testid="stExpander"] > details > summary * {{
    color: {_TEXT} !important;
    font-weight: 600 !important;
    background: transparent !important;
}}
[data-testid="stExpander"] > details > summary:hover {{
    color: {BLUE} !important;
}}
.streamlit-expanderHeader {{
    color: {_TEXT} !important;
    font-weight: 600 !important;
}}

/* ── Alerts ──────────────────────────────── */
[data-testid="stAlert"] {{ border-radius: 8px !important; }}
[data-baseweb="notification"][kind="info"]    {{ border-left: 4px solid {BLUE}   !important; }}
[data-baseweb="notification"][kind="success"] {{ border-left: 4px solid {JADE}   !important; }}
[data-baseweb="notification"][kind="warning"] {{ border-left: 4px solid {ORANGE} !important; }}
[data-baseweb="notification"][kind="error"]   {{ border-left: 4px solid #ef4444  !important; }}

/* ── Caption / small text ────────────────── */
[data-testid="stCaptionContainer"] p {{
    color: {_MUTED} !important;
    font-size: 0.8rem !important;
}}

/* ── Divider ─────────────────────────────── */
hr {{ border-color: {_BORDER} !important; }}

/* ── Dataframe header ────────────────────── */
[data-testid="stDataFrame"] th {{
    background: {NAVY} !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.03em;
}}

/* ── DataFrame card ──────────────────────── */
[data-testid="stDataFrame"] > div {{
    background: {_CARD} !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.35) !important;
    overflow: hidden !important;
    border: 1px solid {_BORDER} !important;
}}

/* ── Chart containers ────────────────────── */
[data-testid="stPlotlyChart"] > div {{
    background: {_CARD} !important;
    border-radius: 10px !important;
    padding: 8px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.35) !important;
    border: 1px solid {_BORDER} !important;
}}

/* ── Slider accent ───────────────────────── */
[data-testid="stSlider"] [role="slider"] {{ background: {BLUE} !important; }}

/* ── Radio label ─────────────────────────── */
[data-testid="stRadio"] label {{ font-weight: 500; color: {_TEXT} !important; }}
</style>""", unsafe_allow_html=True)


# ── Top nav renderer ──────────────────────────────────────────────────────────
def _render_topnav(st_obj, active, conn_env, admin_tok=""):
    logo_b64 = _b64("snaplogic-logo-white.png")

    if conn_env:
        badge_cls = "sl-topnav-badge sl-badge-live"
        badge_txt = f"● {conn_env['name']}"
    else:
        badge_cls = "sl-topnav-badge sl-badge-demo"
        badge_txt = "◌ Demo mode"

    # Append admin token to all nav links so PIN auth survives page navigation
    _qs = f"?{_ADMIN_PARAM}={admin_tok}" if admin_tok else ""

    links_html = ""
    for path, label in NAV_ITEMS:
        href = (f"/{path}" if path else "/") + _qs
        is_active = (label == active)
        cls = "sl-navlink sl-navlink-active" if is_active else "sl-navlink"
        links_html += f'<a href="{href}" class="{cls}" target="_self">{label}</a>\n'

    st_obj.markdown(f"""
<div class="sl-topnav">
  <img src="data:image/png;base64,{logo_b64}" class="sl-topnav-logo" alt="SnapLogic" />
  <div class="sl-topnav-links">
    {links_html}
  </div>
  <span class="{badge_cls}">{badge_txt}</span>
</div>
<div class="sl-nav-spacer"></div>
""", unsafe_allow_html=True)

