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

TRANSFER_OPTIONS = list(range(5_000_000, 200_000_001, 5_000_000))
SALARY_OPTIONS = list(range(1_000_000, 100_000_001, 1_000_000))


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
    seed_row = feas.iloc[-1]
    st.session_state.transfer_budget = random.choice(TRANSFER_OPTIONS)
    st.session_state.salary_budget = random.choice(SALARY_OPTIONS)
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
st.set_page_config(page_title="Optimization Demo", layout="wide")
st.markdown(
    """
    <style>
    .slot-card{background:#1a1d24;padding:10px;border-radius:12px;margin-bottom:8px;border:1px solid #2a2f3a;}
    .slot-label{font-size:12px;color:#9aa;text-transform:uppercase;letter-spacing:1px;}
    .pitch{background:linear-gradient(180deg,#0f5132 0%,#157347 100%);border-radius:16px;padding:16px;}
    .metric-big{font-size:34px;font-weight:700;}
    .over{color:#ff4d4f !important;}
    .ok{color:#52c41a;}
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

with st.expander("❓ Soccer Squad Optimization: A Moneyball-Inspired Decision Optimization Problem", expanded=False):
    st.markdown(
        """
Building a soccer squad is a compelling demonstration of what **PyDO** is designed to solve. Clubs operate under strict constraints—*transfer budgets, wage caps, squad size limits, and positional requirements*—while trying to maximize on-field performance.

Inspired by the **Moneyball philosophy**, the goal is not to acquire the highest-rated players individually, but to identify the **combination of players** that creates the strongest team as a whole. An undervalued player may deliver more performance per dollar than a superstar, allowing resources to be allocated more efficiently across the squad.

In this example, player attributes are transformed into football-specific metrics such as:

- **Attacking Quality**
- **Midfield Creation**
- **Ball Progression**
- **Defensive Strength**
- **Goalkeeping Ability**

These metrics are then aggregated into estimates of:

- **GF (Goals For)** — expected goals scored
- **GA (Goals Against)** — expected goals conceded

The optimizer's objective is simple:

> **Maximize Expected Goal Difference = GF − GA**

while satisfying all roster, budget, and squad-building constraints.

This makes soccer squad construction an ideal showcase for **PyDO**. It combines:

- A clear business objective
- Limited resources
- Multiple competing trade-offs
- Interpretable constraints
- Millions of possible decisions

Rather than selecting players manually, PyDO systematically evaluates vast numbers of squad combinations to identify the roster that delivers the highest expected performance within the available resources.
        """
    )

with st.expander("ℹ️ What is PyDO?", expanded=False):
    st.markdown(
        """
**PyDO (Pythonic Decision Optimizer)** is an open-source framework, powered by Pyomo and Python, solving business decision problems using mathematical optimization.

Instead of manually evaluating thousands or millions of possible choices, users define:

Decision variables — what can be chosen
Objectives — what should be maximized or minimized
Constraints — business rules that must be satisfied

PyDO then automatically finds the optimal solution using state-of-the-art optimization solvers.

The framework is inspired by commercial platforms such as FICO Decision Optimizer but is designed to be fully Python-native, transparent, and accessible to data scientists and analysts.

Typical use cases include:

    - Credit and lending strategy optimization
    - Marketing campaign selection
    - Resource allocation
    - Portfolio optimization
    - Workforce planning
    - Supply chain optimization
    - Sports squad construction and roster management

PyDO aims to bridge the gap between data science and decision science. While machine learning predicts what is likely to happen, PyDO determines what decision should be made to achieve the best outcome under real-world constraints.
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

    st.select_slider(
        "Transfer budget (USD)",
        options=TRANSFER_OPTIONS,
        key="transfer_budget",
        format_func=lambda v: f"${v/1_000_000:.0f}M",
    )
    st.select_slider(
        "Annual salary budget (USD)",
        options=SALARY_OPTIONS,
        key="salary_budget",
        format_func=lambda v: f"${v/1_000_000:.0f}M",
    )

    squad = current_squad()
    transfer_used = sum(df.loc[p, "usd_transfer"] for p in squad.values())
    salary_used = sum(df.loc[p, "usd_salary"] for p in squad.values())

    t_remaining = st.session_state.transfer_budget - transfer_used
    s_remaining = st.session_state.salary_budget - salary_used
    t_over = t_remaining < 0
    s_over = s_remaining < 0

    def money(v):
        return f"${v/1_000_000:,.2f}M"

    bcols = st.columns(2)
    with bcols[0]:
        st.markdown("**Transfer**")
        st.markdown(f"Budget: {money(st.session_state.transfer_budget)}")
        st.markdown(f"Used: {money(transfer_used)}")
        cls = "over" if t_over else "ok"
        st.markdown(
            f"<div class='metric-big {cls}'>Remaining: {money(t_remaining)}</div>",
            unsafe_allow_html=True,
        )
    with bcols[1]:
        st.markdown("**Salary**")
        st.markdown(f"Budget: {money(st.session_state.salary_budget)}")
        st.markdown(f"Used: {money(salary_used)}")
        cls = "over" if s_over else "ok"
        st.markdown(
            f"<div class='metric-big {cls}'>Remaining: {money(s_remaining)}</div>",
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
        mcols[2].metric("GA (defense)", f"-{scores['GA']:.3f}")
    except Exception as e:
        st.warning(f"Cannot evaluate: {e}")

    st.divider()

    if st.button("🚀 Let PyDO do its magic!", type="primary", use_container_width=True):
        row = lookup_optimal(st.session_state.transfer_budget, st.session_state.salary_budget)
        if row is None:
            st.error("No feasible optimal team for these budgets.")
        else:
            apply_team(row)
            st.success(
                f"Loaded optimal squad — GF={row['GF_index']:.2f}, GA={row['GA_index']:.2f}"
            )
            st.rerun()

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

