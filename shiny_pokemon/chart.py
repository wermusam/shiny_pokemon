"""Plotly chart for shiny probability visualization."""

import plotly.graph_objects as go
from shiny_pokemon.shiny import ShinyOdds


def build_chart(game: ShinyOdds, max_resets: int = 30000) -> go.Figure:
    """Build an interactive chart showing probability vs attempts.

    Args:
        game: ShinyOdds instance with the odds to plot.
        max_resets: How far along the x-axis to go.

    Returns:
        A Plotly Figure ready to display or save.
    """
    resets = list(range(0, max_resets + 1, 50))
    probabilities = [game.cumulative_probability(r) * 100 for r in resets]

    milestones = [1000, 5000, 8192, 15000, 25000]
    milestone_x = []
    milestone_y = []
    milestone_text = []
    for n in milestones:
        if n <= max_resets:
            prob = game.cumulative_probability(n) * 100
            milestone_x.append(n)
            milestone_y.append(prob)
            milestone_text.append(f"{n:,} attempts → {prob:.1f}%")

    one_attempt = game.cumulative_probability(1) * 100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=resets,
        y=probabilities,
        mode="lines",
        name="Cumulative Probability",
        line=dict(color="#FFD700", width=3),
        hovertemplate="Attempts: %{x:,}<br>Probability: %{y:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=milestone_x,
        y=milestone_y,
        mode="markers+text",
        name="Milestones",
        text=milestone_text,
        textposition="bottom right",
        textfont=dict(size=10, color="white"),
        marker=dict(size=8, color="#FF6B6B"),
        hovertemplate="%{text}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text=(
                f"Shiny Pokemon Probability For {game.name}"
                f"<br><sub>P(n) = 1 - ((odds - 1) ÷ odds)ⁿ"
                f"  |  1 attempt = {one_attempt:.4f}%</sub>"
            ),
            x=0.5,
            font=dict(size=20),
        ),
        xaxis_title="Number of Attempts",
        yaxis_title="Probability of Getting 1 Shiny Pokemon(%)",
        template="plotly_dark",
        yaxis=dict(range=[0, 105]),
        showlegend=False,
    )

    return fig
