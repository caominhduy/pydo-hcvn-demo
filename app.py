"""
Squad Optimization Demo (Streamlit)
-----------------------------------
Run:
    pip install streamlit pandas
    streamlit run app.py

Files expected next to this script:
    - players.csv
    - optimal_teams.csv
"""

import os
import random
import base64
import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_players() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(HERE, "players.csv"))
    df = df.set_index("name", drop=False)
    return df


@st.cache_data
def load_optimal() -> pd.DataFrame:
    return pd.read_csv(os.path.join(HERE, "optimal_teams.csv"))


df = load_players()
opt_df = load_optimal()

SLOTS = ["GK", "CB1", "CB2", "CB3", "CM1", "CM2", "CM3", "CM4", "CM5", "ST1", "ST2"]

GK_PLAYERS = df[df["flag_goalkeeper"] == 1]["name"].tolist()
OUTFIELD_PLAYERS = df[df["flag_goalkeeper"] == 0]["name"].tolist()

INFINITY_BUDGET = 999_999_999
PYDO_PASSWORD = "ds@hcvn"
TRANSFER_OPTIONS = list(range(5_000_000, 200_000_001, 5_000_000)) + [INFINITY_BUDGET]
SALARY_OPTIONS = list(range(1_000_000, 100_000_001, 1_000_000)) + [INFINITY_BUDGET]


# ---------------------------------------------------------------------------
# Evaluation (provided by user)
# ---------------------------------------------------------------------------
def evaluate_squad(result, df=df):
    st_attack = (df.loc[result["ST1"], "ST_attack_L"] + df.loc[result["ST2"], "ST_attack_R"]) / 2
    mid_attack = (
        df.loc[result["CM1"], "MID_creation_L"]
        + df.loc[result["CM2"], "MID_creation_L"]
        + df.loc[result["CM3"], "MID_creation"]
        + df.loc[result["CM4"], "MID_creation_R"]
        + df.loc[result["CM5"], "MID_creation_R"]
    ) / 5
    progression = (
        df.loc[result["CB1"], "progression_L"]
        + df.loc[result["CB2"], "progression"]
        + df.loc[result["CB3"], "progression_R"]
        + df.loc[result["CM1"], "progression_L"]
        + df.loc[result["CM2"], "progression_L"]
        + df.loc[result["CM3"], "progression"]
        + df.loc[result["CM4"], "progression_R"]
        + df.loc[result["CM5"], "progression_R"]
        + df.loc[result["ST1"], "progression_L"]
        + df.loc[result["ST2"], "progression_R"]
    ) / 10
    GF = (0.45 * st_attack + 0.35 * mid_attack + 0.20 * progression) / 20

    cb_defense = (
        df.loc[result["CB1"], "CB_defense_L"]
        + df.loc[result["CB2"], "CB_defense"]
        + df.loc[result["CB3"], "CB_defense_R"]
    ) / 3
    mid_defense = (
        df.loc[result["CM1"], "MID_creation_L"]
        + df.loc[result["CM2"], "MID_creation_L"]
        + df.loc[result["CM3"], "MID_creation"]
        + df.loc[result["CM4"], "MID_creation_R"]
        + df.loc[result["CM5"], "MID_creation_R"]
    ) / 5
    gk_defense = df.loc[result["GK"], "GK_defense"]
    GA = (0.50 * cb_defense + 0.20 * mid_defense + 0.30 * gk_defense) / 20

    return {"objective": GF - GA, "GF": GF, "GA": GA}


def lookup_optimal(transfer_budget: int, salary_budget: int):
    """Find row in optimal_teams.csv matching the budgets (nearest <=)."""
    sub = opt_df[
        (opt_df["transfer_budget"] == transfer_budget)
        & (opt_df["salary_budget"] == salary_budget)
        & (opt_df["feasible"] == True)  # noqa: E712
    ]
    if sub.empty:
        # fall back: largest feasible row not exceeding budgets
        sub = opt_df[
            (opt_df["transfer_budget"] <= transfer_budget)
            & (opt_df["salary_budget"] <= salary_budget)
            & (opt_df["feasible"] == True)  # noqa: E712
        ]
        if sub.empty:
            return None
        sub = sub.sort_values(["transfer_budget", "salary_budget"], ascending=False).head(1)
    return sub.iloc[0]


# ---------------------------------------------------------------------------
# Session state init — random feasible starting team
# ---------------------------------------------------------------------------
def init_state():
    if "initialized" in st.session_state:
        return
    feas = opt_df[opt_df["feasible"] == True]  # noqa: E712
    if len(feas) > 1:
        seed_rows = feas.sample(2)
        seed_row = seed_rows.iloc[0]
        budget_row = seed_rows.iloc[1]
    else:
        seed_row = budget_row = feas.iloc[0]
    st.session_state.transfer_budget = int(budget_row["transfer_budget"])
    st.session_state.salary_budget = int(budget_row["salary_budget"])
    for s in SLOTS:
        st.session_state[f"slot_{s}"] = seed_row[s]
    st.session_state.initialized = True


init_state()

# Apply any pending squad BEFORE slot widgets are instantiated.
# Streamlit forbids mutating a widget's session_state key after the
# widget has been created on this run, so Optimize stages the update
# here and triggers a rerun.
if "pending_squad" in st.session_state:
    pending = st.session_state.pop("pending_squad")
    for s in SLOTS:
        st.session_state[f"slot_{s}"] = pending[s]


def apply_team(row):
    st.session_state["pending_squad"] = {s: row[s] for s in SLOTS}


def current_squad():
    return {s: st.session_state[f"slot_{s}"] for s in SLOTS}


def budget_label(v: int) -> str:
    if v == INFINITY_BUDGET:
        return "∞"
    return f"${v/1_000_000:.0f}M"


def set_infinity_budget(key: str):
    st.session_state[key] = INFINITY_BUDGET


def render_pydo_confetti():
    pieces = "".join(
        f"<span style='--x:{x}px;--y:{y}px;--r:{r}deg;--c:{color};--d:{delay}ms'></span>"
        for x, y, r, color, delay in [
            (-86, -56, -34, "#ff4d4f", 0),
            (-68, -78, 18, "#fadb14", 40),
            (-44, -62, 47, "#52c41a", 80),
            (-24, -90, -16, "#1677ff", 20),
            (-8, -66, 31, "#ff85c0", 70),
            (18, -86, -42, "#fa8c16", 30),
            (36, -58, 12, "#13c2c2", 90),
            (58, -76, -28, "#9254de", 50),
            (82, -52, 39, "#73d13d", 110),
            (-96, -30, 22, "#ffd666", 120),
            (96, -34, -18, "#69c0ff", 140),
            (0, -104, 8, "#ff7875", 60),
        ]
    )
    st.markdown(
        f"""
        <style>
        .pydo-confetti{{height:82px;margin-top:-78px;margin-bottom:-4px;position:relative;pointer-events:none;overflow:visible;}}
        .pydo-confetti span{{
            animation:pydo-burst 900ms ease-out both;
            background:var(--c);
            border-radius:2px;
            bottom:10px;
            height:9px;
            left:50%;
            opacity:0;
            position:absolute;
            transform:translate(-50%, 0) rotate(0deg);
            width:6px;
        }}
        @keyframes pydo-burst{{
            0%{{opacity:0;transform:translate(-50%, 0) scale(.6) rotate(0deg);}}
            12%{{opacity:1;}}
            100%{{opacity:0;transform:translate(calc(-50% + var(--x)), var(--y)) scale(1) rotate(var(--r));}}
        }}
        .pydo-confetti span{{animation-delay:var(--d);}}
        </style>
        <div class="pydo-confetti">{pieces}</div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers — option labels with stats tooltip
# ---------------------------------------------------------------------------
# Human-friendly names for every stat column in players.csv
STAT_LABELS = {
    "sprintspeed": "Sprint Speed", "acceleration": "Acceleration",
    "finishing": "Finishing", "shotpower": "Shot Power", "longshots": "Long Shots",
    "positioning": "Positioning", "volleys": "Volleys", "penalties": "Penalties",
    "shortpassing": "Short Passing", "vision": "Vision", "crossing": "Crossing",
    "longpassing": "Long Passing", "freekickaccuracy": "Free Kick Accuracy",
    "curve": "Curve", "dribbling": "Dribbling", "ballcontrol": "Ball Control",
    "agility": "Agility", "balance": "Balance", "reactions": "Reactions",
    "marking": "Marking", "standingtackle": "Standing Tackle",
    "interceptions": "Interceptions", "headingaccuracy": "Heading Accuracy",
    "slidingtackle": "Sliding Tackle", "strength": "Strength",
    "stamina": "Stamina", "aggression": "Aggression", "jumping": "Jumping",
    "composure": "Composure",
    "gkdiving": "GK Diving", "gkhandling": "GK Handling",
    "gkkicking": "GK Kicking", "gkreflexes": "GK Reflexes",
    "gkpositioning": "GK Positioning",
    "left_foot": "Left Foot",
    "right_foot": "Right Foot"
}

STAT_GROUPS_OUTFIELD = {
    "Pace": ["sprintspeed", "acceleration"],
    "Shooting": ["finishing", "shotpower", "longshots", "positioning", "volleys", "penalties"],
    "Passing": ["shortpassing", "vision", "crossing", "longpassing", "freekickaccuracy", "curve"],
    "Dribbling": ["dribbling", "ballcontrol", "agility", "balance", "reactions"],
    "Defending": ["marking", "standingtackle", "interceptions", "headingaccuracy", "slidingtackle"],
    "Physical": ["strength", "stamina", "aggression", "jumping", "composure"],
    "Footedness": ['left_foot', 'right_foot'],
}
STAT_GROUPS_GK = {
    "Goalkeeping": ["gkdiving", "gkhandling", "gkkicking", "gkreflexes", "gkpositioning"],
    "Physical": ["reactions", "jumping", "strength", "composure"],
    "Footedness": ['left_foot', 'right_foot'],
}


def extract_pid(stats_url: str) -> str:
    """`https://en.fifaaddict.com/fo4db/pidXXXX` -> `XXXX`."""
    if not isinstance(stats_url, str):
        return ""
    last = stats_url.rstrip("/").split("/")[-1]
    return last[3:] if last.startswith("pid") else last


# def player_image_url(name: str) -> str:
#     pid = extract_pid(df.loc[name, "stats_url"])
#     return f"https://s1.fifaaddict.com/fo4/players/{pid}.png" if pid else ""

def player_image_url(name: str) -> str:
    pid = extract_pid(df.loc[name, "stats_url"])
    return f"https://raw.githubusercontent.com/caominhduy/pydo-hcvn-demo/refs/heads/main/images/{pid}.png" if pid else ""


def player_image_html(name: str, width: int = 80) -> str:
    url = player_image_url(name)
    if not url:
        return ""
    return (
        f'<img src="{url}" width="{width}" '
        f'style="border-radius:8px;border:1px solid #333;background:#111;" '
        f'onerror="this.style.display=\'none\'" />'
    )


def render_player_stats(name: str):
    """Show full stat block for a player using human-friendly labels."""
    row = df.loc[name]
    is_gk = row["flag_goalkeeper"] == 1
    groups = STAT_GROUPS_GK if is_gk else STAT_GROUPS_OUTFIELD
    st.markdown(
        f"<div style='font-size:12px;color:#9aa;'>Transfer "
        f"<b>${row['usd_transfer']/1_000_000:.2f}M</b> · Salary "
        f"<b>${row['usd_salary']/1_000_000:.2f}M</b></div>",
        unsafe_allow_html=True,
    )
    rows = []
    for group, keys in groups.items():
        for k in keys:
            if k not in df.columns:
                continue
            try:
                val = int(row[k])
            except Exception:
                val = row[k]
            rows.append({"Group": group, "Attribute": STAT_LABELS.get(k, k), "Value": val})
    stats_df = pd.DataFrame(rows)
    st.dataframe(stats_df, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Optimization Demo", layout="wide", page_icon="./hcvn.ico")
st.markdown(
    """
    <style>
    .slot-card{background:#1a1d24;padding:10px;border-radius:12px;margin-bottom:8px;border:1px solid #2a2f3a;}
    .slot-label{font-size:12px;color:#9aa;text-transform:uppercase;letter-spacing:1px;}
    .pitch{background:linear-gradient(180deg,#0f5132 0%,#157347 100%);border-radius:16px;padding:16px;}
    .metric-big{font-size:34px;font-weight:700;}
    .over{color:#ff4d4f !important;}
    .ok{color:#52c41a;}
    .st-key-transfer_infinity button,
    .st-key-salary_infinity button{
        font-size:22px !important;
        font-weight:700 !important;
        line-height:1 !important;
        min-height:40px;
        padding-top:6px !important;
        padding-bottom:6px !important;
    }
    .st-key-transfer_infinity button p,
    .st-key-salary_infinity button p{
        font-size:22px !important;
        font-weight:700 !important;
        line-height:1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("HCVN Expo x PyDO")
st.title("⚽ A MONEYBALL-INSPIRED OPTIMIZATION GAME")
st.subheader("Try your best to maximize objective on the budget (the odd is 1/3E18), good luck!")

st.markdown(
    f"""
    <div style="
        color: #999;
        font-size: 0.75rem;
        opacity: 0.6;
        margin-bottom: 1rem;
    ">
        Seriously, if you have not seen <a href='https://www.imdb.com/title/tt1210166/'>Moneyball</a>, watch it tonight!
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("💡 How to play", expanded=False):
    st.markdown(
        """
**Objective:** Maximize **GF − GA** (score more goals, concede fewer goals).

#### Increase GF

- **45% Strikers** → Prioritize Finishing, Positioning, Shot Power, Composure, Volleys.
- **35% Midfield Creation** → Prioritize Vision, Short Passing, Long Passing, Ball Control, Dribbling.
- **20% Progression** → Prioritize Speed, Acceleration, Agility, Dribbling, Ball Control.
- Consider **footedness**: left-footed players are more valuable on the left side, right-footed players on the right.

#### Reduce GA

- **50% Centre-Backs** → Prioritize Marking, Interceptions, Tackling, Strength, Jumping.
- **30% Goalkeeper** → Prioritize Reflexes, Diving, Handling, Positioning.
- **20% Midfield Defense** → Prioritize Interceptions, Stamina, Aggression, Strength.

#### Budget Strategy

- Spend heavily on **strikers and centre-backs**; they have the largest impact on the objective.
- Look for midfielders that contribute to both attack and defense.
- Avoid overspending on players whose strengths affect only one component of the model.

#### Why This Is Hard

Every player influences multiple metrics simultaneously. Replacing a single midfielder can change creation, progression, defense, budget allocation, and even the value of other players around him.

With hundreds or thousands of available players, the number of possible squads becomes enormous. Even if you understand the formulas perfectly, finding the best squad manually is effectively impossible—which is precisely why decision optimization exists.
        """
    )

with st.expander("🎯 From Moneyball to Consumer Finance: The Same Optimization Problem", expanded=False):
    st.markdown(
        """
The movie [Moneyball](https://www.imdb.com/title/tt1210166) popularized a simple idea:

> **Winning is not about acquiring the best individuals. It's about finding the combination of assets that produces the best overall outcome within a limited budget.**

That idea is exactly what **Decision Optimization** is about.

Whether you are building a soccer squad or optimizing a cross-sell cash loan campaign at Home Credit Vietnam, the underlying problem is the same:

| ⚽ Moneyball Soccer Squad | 💰 Cross-Sell Cash Loan |
|--------------------------|-------------------------|
| Players | Existing customers |
| Maximize Goal Difference (GF − GA) | Maximize Expected Profit |
| Transfer budget | Business KPIs |
| Position requirements | Segment/channel quotas |
| Left/right foot balance | Sensitivity to product's parameters |
| Squad size limit | Volume limit |
| Player attributes | Customer features & model scores |

### ⚽ Soccer Example

In the soccer demo, PyDO evaluates thousands of players and selects the squad that maximizes expected performance.

The optimizer balances:

- Attacking quality (Goals For)
- Defensive quality (Goals Against)
- Transfer budget
- Positional requirements
- Squad composition

A superstar striker may score more goals, but his cost might prevent strengthening the defense elsewhere. The optimal squad is therefore often **not** the collection of the highest-rated players.

### 💰 Home Credit Example

The exact same logic applies to cross-sell optimization.

The objective is to maximize:

> **Interest Income + Fee Income − Credit Losses − Funding Cost − Operational Cost...**

while satisfying constraints such as:

- Risk appetite by customer segment
- Acquisition channel requirement
- Budget limits
- Regulatory requirements
- Portfolio concentration limits

A customer with the highest response probability is not necessarily the most profitable customer if they also carry high default risk or consume scarce channel capacity. Similarly, a higher price point is not necessarily a better decision if client does not agree on and take the loan.
        """
    )

with st.expander("🚀 Why PyDO?", expanded=False):
    st.markdown(
        """
Historically, organizations have used commercial platforms such as **FICO Decision Optimizer** to solve these problems.

PyDO (Pythonic Decision Optimizer) demonstrates that the same optimization methodology can be implemented using open-source technologies such as Python, Pyomo, and SCIP. It is thus native, transparent, and accessible to data scientists and analysts.

The result is a framework that can produce solutions comparable to commercial decision optimization platforms while remaining:

- ✅ Open-source
- ✅ Transparent
- ✅ Extensible
- ✅ Cost-free

Whether selecting a soccer squad or allocating a lending portfolio, the question is always the same:

> **Given limited resources and many constraints, what combination of decisions creates the best overall outcome?**

PyDO aims to bridge the gap between data science and decision science. While machine learning predicts what is likely to happen, PyDO determines what decision should be made to achieve the best outcome under real-world constraints.

That is precisely the problem PyDO is built to solve.
        """
    )

left, right = st.columns([1.8, 1])

# ---------------- LEFT: Squad selection ----------------
with left:
    st.subheader("Squad")

    def slot_selector(slot: str, options: list):
        chosen_others = {
            st.session_state[f"slot_{s}"] for s in SLOTS if s != slot
        }
        avail = [p for p in options if p not in chosen_others]
        current = st.session_state[f"slot_{slot}"]
        if current not in avail:
            avail = [current] + avail
        idx = avail.index(current)
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                st.markdown(player_image_html(current, 70), unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"<div class='slot-label'>{slot}</div>", unsafe_allow_html=True)
                st.selectbox(
                    label=slot,
                    options=avail,
                    index=idx,
                    key=f"slot_{slot}",
                    label_visibility="collapsed",
                )
            with st.expander("Stats", expanded=False):
                render_player_stats(st.session_state[f"slot_{slot}"])

    # Strikers row
    st.markdown("**Strikers**")
    c = st.columns(2)
    with c[0]: slot_selector("ST1", OUTFIELD_PLAYERS)
    with c[1]: slot_selector("ST2", OUTFIELD_PLAYERS)

    st.markdown("**Midfielders**")
    c = st.columns(5)
    for i, s in enumerate(["CM1", "CM2", "CM3", "CM4", "CM5"]):
        with c[i]: slot_selector(s, OUTFIELD_PLAYERS)

    st.markdown("**Defenders**")
    c = st.columns(3)
    for i, s in enumerate(["CB1", "CB2", "CB3"]):
        with c[i]: slot_selector(s, OUTFIELD_PLAYERS)

    st.markdown("**Goalkeeper**")
    slot_selector("GK", GK_PLAYERS)

    # Duplicate guard
    squad = current_squad()
    if len(set(squad.values())) != len(squad):
        st.error("Duplicate players selected — please change them.")

# ---------------- RIGHT: Budgets & Scores ----------------
with right:
    # ---- Budgets ----
    st.subheader("Budgets")

    transfer_cols = st.columns([5, 1])
    with transfer_cols[0]:
        st.select_slider(
            "Transfer budget (USD)",
            options=TRANSFER_OPTIONS,
            key="transfer_budget",
            format_func=budget_label,
        )
    with transfer_cols[1]:
        st.button(
            "∞",
            key="transfer_infinity",
            type="primary",
            on_click=set_infinity_budget,
            args=("transfer_budget",),
            use_container_width=True,
        )

    salary_cols = st.columns([5, 1])
    with salary_cols[0]:
        st.select_slider(
            "Annual salary budget (USD)",
            options=SALARY_OPTIONS,
            key="salary_budget",
            format_func=budget_label,
        )
    with salary_cols[1]:
        st.button(
            "∞",
            key="salary_infinity",
            type="primary",
            on_click=set_infinity_budget,
            args=("salary_budget",),
            use_container_width=True,
        )

    squad = current_squad()
    transfer_used = sum(df.loc[p, "usd_transfer"] for p in squad.values())
    salary_used = sum(df.loc[p, "usd_salary"] for p in squad.values())

    t_remaining = st.session_state.transfer_budget - transfer_used
    s_remaining = st.session_state.salary_budget - salary_used
    t_over = t_remaining < 0
    s_over = s_remaining < 0

    def money(v):
        if v == INFINITY_BUDGET:
            return "∞"
        return f"${v/1_000_000:,.2f}M"

    t_remaining_label = "∞" if st.session_state.transfer_budget == INFINITY_BUDGET else money(t_remaining)
    s_remaining_label = "∞" if st.session_state.salary_budget == INFINITY_BUDGET else money(s_remaining)

    bcols = st.columns(2)
    with bcols[0]:
        st.markdown("**Transfer**")
        st.markdown(f"🎯 Budget: {money(st.session_state.transfer_budget)}")
        st.markdown(f"💸 Used: {money(transfer_used)}")
        cls = "over" if t_over else "ok"
        st.markdown(
            f"<div class='metric-big {cls}'>Remaining: {t_remaining_label}</div>",
            unsafe_allow_html=True,
        )
    with bcols[1]:
        st.markdown("**Salary**")
        st.markdown(f"🎯 Budget: {money(st.session_state.salary_budget)}")
        st.markdown(f"💸 Used: {money(salary_used)}")
        cls = "over" if s_over else "ok"
        st.markdown(
            f"<div class='metric-big {cls}'>Remaining: {s_remaining_label}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ---- Scores ----
    st.subheader("Team Score (higher is better)")
    try:
        scores = evaluate_squad(squad)
        mcols = st.columns(3)
        mcols[0].metric("Objective", f"{scores['objective']:.3f}")
        mcols[1].metric("GF (attack)", f"{scores['GF']:.3f}")
        mcols[2].metric("GA (defense)", f"{scores['GA']:.3f}")
    except Exception as e:
        st.warning(f"Cannot evaluate: {e}")

    st.divider()

    show_pydo_confetti = st.session_state.pop("show_pydo_confetti", False)

    pydo_password = st.text_input(
        "Password",
        type="password",
        key="pydo_password",
    )
    if st.button("🚀 Let PyDO do its magic!", type="primary", use_container_width=True):
        if pydo_password != PYDO_PASSWORD:
            st.error("Incorrect password.")
        else:
            row = lookup_optimal(st.session_state.transfer_budget, st.session_state.salary_budget)
            if row is None:
                st.error("No feasible optimal team for these budgets.")
            else:
                apply_team(row)
                st.session_state["show_pydo_confetti"] = True
                st.success(
                    f"Loaded optimal squad — GF={row['GF_index']:.2f}, GA={row['GA_index']:.2f}"
                )
                st.rerun()
    if show_pydo_confetti:
        render_pydo_confetti()

credit = 'Duy Cao, Home Credit Vietnam, 2026'
statement = '"Of the 20,000 notable players for us to consider, I believe that there is a championship team of twenty-five people that we can afford, because everyone else in baseball undervalues them." Brand, Moneyball'
st.markdown(
    f"""
    <hr style="margin-top: 4rem; opacity: 0.2;">
    <div style="
        text-align: center;
        color: #999;
        font-size: 0.75rem;
        opacity: 0.6;
    ">
        {credit}
    </div>
    <br>
    <div style="
        text-align: center;
        color: #999;
        font-size: 0.75rem;
        opacity: 0.6;
    ">
        {statement}
    </div>
    """,
    unsafe_allow_html=True,
)
