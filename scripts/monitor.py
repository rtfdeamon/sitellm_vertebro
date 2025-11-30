"""Console dashboard showing crawler and DB status using Rich."""

from time import sleep
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from packages.core.status import status_dict


def render():
    """Build a Rich renderable with current status metrics."""
    s = status_dict()
    t = Table(title="Crawler & DB status", expand=True)
    t.add_column("Metric", style="bold cyan")
    t.add_column("Value", style="bold")

    t.add_row("Fill %", f"{s['fill_percent']}% (target {s['db']['target_docs']})")
    t.add_row("Mongo docs", str(s['db']['mongo_docs']))
    t.add_row("Qdrant points", str(s['db']['qdrant_points']))
    t.add_row("Queued", str(s['crawler']['queued']))
    t.add_row("In progress", str(s['crawler']['in_progress']))
    t.add_row("Done", str(s['crawler']['done']))
    t.add_row("Failed", str(s['crawler']['failed']))
    t.add_row("Last URL", str(s['crawler']['last_url'] or '—'))
    freshness = s.get("freshness")
    age = f"{freshness/3600:.1f}h ago" if freshness is not None else "unknown"
    stale = freshness is None or freshness > 24 * 3600
    color = "red" if stale else "green"
    last_iso = s.get("last_crawl_iso") or "—"
    t.add_row("Last crawl", f"[{color}]{last_iso} ({age})[/]")

    p = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        expand=True,
    )
    task = p.add_task("DB fill", total=100)
    p.update(task, completed=min(100, int(s['fill_percent'])))

    return Panel.fit(
        Table.grid(expand=True).add_row(t).add_row(p),
        title="Sitellm Vertebro Monitor",
        border_style="magenta",
    )


def main():
    """Continuously refresh the dashboard in the terminal."""
    with Live(render(), refresh_per_second=2, screen=False) as live:
        while True:
            sleep(0.5)
            live.update(render())


if __name__ == "__main__":
    main()
