"""Command line interface for shiny pokemon probability calculator."""

import click
from shiny_pokemon.shiny import ShinyOdds
from shiny_pokemon.chart import build_chart

@click.command()
@click.option("--odds", default=8192, help="Shiny odds (e.g., 8192 for Fire Red, 4096 for modern games).")
@click.option("--name", default="Fire Red", help="Game generation name.")
@click.option("--resets", default=30000, help="Number of soft resets to calculate probability for.")
def main(odds: int, name: str, resets: int) -> None:
    """Generate shiny probability chart"""
    game = ShinyOdds(name=name, odds=odds)
    fig = build_chart(game, max_resets=resets)
    fig.write_html("shiny_chart.html")
    click.echo(f"Chart saved to shiny_chart.html")

if __name__ == "__main__":
    main()