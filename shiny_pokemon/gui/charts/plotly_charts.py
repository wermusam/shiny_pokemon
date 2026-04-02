"""Plotly charts rendered inside PySide6 via QWebEngineView.

Each chart function returns an HTML string that can be loaded
into a QWebEngineView with .setHtml(html).
"""

import plotly.graph_objects as go
from shiny_pokemon.shiny import ShinyOdds


def _make_responsive(fig: go.Figure) -> str:
    """Convert a Plotly figure to responsive HTML.

    Makes the chart fill its container and resize with the window.
    """
    html = fig.to_html(
        include_plotlyjs=True,
        full_html=True,
        config={"responsive": True},
    )
    # Inject CSS to make the chart fill the entire page with no scrollbars
    resize_css = """
    <style>
        html, body { margin: 0; padding: 0; overflow: hidden;
                     width: 100%; height: 100%; }
        .plotly-graph-div { width: 100% !important;
                            height: 100% !important; }
    </style>
    """
    html = html.replace("</head>", resize_css + "</head>")
    return html


def analytical_chart_html(
    effective_probability: float,
    game_name: str,
    target_name: str,
    max_encounters: int = 30000,
) -> str:
    """Build an interactive Plotly chart showing cumulative probability.

    This is the analytical (mathematical) view — the exact formula.
    """
    effective_odds = round(1 / effective_probability)
    game = ShinyOdds(name=game_name, odds=effective_odds)

    step = max(1, max_encounters // 600)
    encounters = list(range(0, max_encounters + 1, step))
    probabilities = [game.cumulative_probability(n) * 100 for n in encounters]

    # Only show a few milestones to avoid overlap
    milestones = [50, 90]
    m_x = []
    m_y = []
    m_text = []
    for pct in milestones:
        n = game.resets_for_probability(pct / 100)
        if n <= max_encounters:
            m_x.append(n)
            m_y.append(pct)
            m_text.append(f"{pct}% chance after {n:,} tries")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=encounters,
        y=probabilities,
        mode="lines",
        name="Your odds over time",
        line=dict(color="#FFD700", width=3),
        hovertemplate="After %{x:,} tries<br>You have a %{y:.1f}% chance<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=m_x,
        y=m_y,
        mode="markers+text",
        name="Key milestones",
        text=m_text,
        textposition="bottom right",
        textfont=dict(size=11, color="white"),
        marker=dict(size=10, color="#FF6B6B"),
        hovertemplate="%{text}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text=(
                f"How likely am I to find a Shiny {target_name}?"
                f"<br><sub>Each try has a 1 in {effective_odds:,} chance "
                f"({game_name})</sub>"
            ),
            x=0.5,
            font=dict(size=18),
        ),
        xaxis_title="Number of Tries (encounters or resets)",
        yaxis_title="Your Chance of Finding a Shiny (%)",
        template="plotly_dark",
        yaxis=dict(range=[0, 105]),
        showlegend=False,
        margin=dict(l=60, r=30, t=80, b=50),
    )

    return _make_responsive(fig)


def simulation_histogram_html(
    attempts: list[int],
    effective_probability: float,
    target_name: str,
    analytical_mean: float,
    analytical_median: float,
) -> str:
    """Build a histogram of simulation results with analytical overlays.

    This is the Monte Carlo view — results from simulated hunts.
    """
    if not attempts:
        fig = go.Figure()
        fig.update_layout(
            title="Run a simulation to see results here",
            template="plotly_dark",
        )
        return _make_responsive(fig)

    import numpy as np
    arr = np.array(attempts)
    sim_mean = float(np.mean(arr))
    sim_median = float(np.median(arr))

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=attempts,
        nbinsx=80,
        name="Simulated hunters",
        marker_color="#4ECDC4",
        opacity=0.8,
        hovertemplate="Took %{x:,} tries<br>%{y} hunters<extra></extra>",
    ))

    # Two reference lines — the math answer vs the simulation answer
    # These should be close but not identical. That's Monte Carlo!
    fig.add_vline(
        x=analytical_mean, line_dash="dash", line_color="#FFD700", line_width=2,
        annotation_text=f"Math says: {analytical_mean:,.0f}",
        annotation_position="top right",
        annotation_font_color="#FFD700",
        annotation_font_size=12,
    )
    fig.add_vline(
        x=sim_mean, line_dash="solid", line_color="#FF6B6B", line_width=2,
        annotation_text=f"Simulation got: {sim_mean:,.0f}",
        annotation_position="top left",
        annotation_font_color="#FF6B6B",
        annotation_font_size=12,
    )

    # How close did the simulation get to the math?
    diff_pct = abs(sim_mean - analytical_mean) / analytical_mean * 100
    if diff_pct < 2:
        accuracy_msg = f"Simulation is within {diff_pct:.1f}% of the math. Very close!"
    elif diff_pct < 5:
        accuracy_msg = f"Simulation is {diff_pct:.1f}% off from the math. Pretty good!"
    else:
        accuracy_msg = f"Simulation is {diff_pct:.1f}% off. Try more hunters for better accuracy"

    fig.update_layout(
        title=dict(
            text=(
                f"What if {len(attempts):,} people all hunted Shiny {target_name}?"
                f"<br><sub>{accuracy_msg}</sub>"
            ),
            x=0.5,
            font=dict(size=16),
        ),
        xaxis_title="How many tries it took",
        yaxis_title="How many hunters",
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=60, r=30, t=85, b=50),
    )

    return _make_responsive(fig)


def empty_chart_html(message: str = "Pick a route and Pokemon to get started!") -> str:
    """Placeholder chart shown before any selection is made."""
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=message, x=0.5, font=dict(size=16)),
        template="plotly_dark",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return _make_responsive(fig)
