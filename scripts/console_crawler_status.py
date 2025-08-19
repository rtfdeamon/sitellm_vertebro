from time import sleep
from rich.table import Table
from rich.live import Live
from rich import box
from backend.crawler_reporting import Reporter


def render(rows):
    t = Table(title="Crawler status", box=box.SIMPLE_HEAVY)
    t.add_column("Job")
    t.add_column("Queued")
    t.add_column("Fetched")
    t.add_column("Parsed")
    t.add_column("Indexed")
    t.add_column("Errors")
    t.add_column("Last URL", overflow="fold")
    t.add_column("Done")
    for key, d in rows.items():
        t.add_row(
            key.split(":")[-1],
            str(d.get("queued", 0)),
            str(d.get("fetched", 0)),
            str(d.get("parsed", 0)),
            str(d.get("indexed", 0)),
            str(d.get("errors", 0)),
            str(d.get("last_url", "")[:120]),
            "✅" if str(d.get("done", "False")).lower() in {"true", "1"} else "…",
        )
    return t


def main() -> None:
    rep = Reporter()
    with Live(refresh_per_second=2) as live:
        while True:
            rows = rep.get_all()
            live.update(render(rows))
            sleep(1.0)


if __name__ == "__main__":
    main()
