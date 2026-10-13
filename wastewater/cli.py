"""Command line: fetch the reports, link discharges with bathing waters, render the page and the signals."""
from __future__ import annotations

import typer

from . import analysis, signals, web
from .config import DATA_DIR
from .sources import bathing, uwwtd
from .store import read_json, write_json

app = typer.Typer(add_completion=False, help="Depuración y baño: urban waste water and the bathing waters downstream.")
VERSIONS = DATA_DIR / "versions.json"


def _current() -> dict:
    """What the sources publish now: the date Spain sent its UWWTD report and the latest bathing release."""
    rows = uwwtd.query_report()
    rel = bathing.latest_release()
    return {"uwwtd": rows["version"], "bathing": f'{rel["season"]} v{rel["version"]} {rel["uuid"]}'}


@app.command()
def check():
    """Exit 0 if a source has a new release (prints what changed), 1 if everything is up to date."""
    now, seen = _current(), read_json(VERSIONS, {})
    changed = {k: v for k, v in now.items() if seen.get(k) != v}
    for k, v in changed.items():
        typer.echo(f"{k}: {seen.get(k)} -> {v}")
    raise typer.Exit(0 if changed else 1)


@app.command()
def fetch():
    """Download the UWWTD tables and the latest bathing water classification and register."""
    for name, n in uwwtd.fetch().items():
        typer.echo(f"uwwtd {name}: {n}")
    rel = bathing.latest_release()
    typer.echo(f"bathing {rel['season']} v{rel['version']}: {bathing.fetch_status(rel)} rows, "
               f"{bathing.fetch_zones()} registered bathing waters")
    write_json(VERSIONS, _current())


@app.command()
def link():
    """Follow every discharge point downstream (HydroRIVERS) and write data/links.json."""
    typer.echo(f"{analysis.build_links()} discharge -> bathing water links")


@app.command()
def page():
    """Render docs/index.html and docs/signals.json from the stored data."""
    data = analysis.build()
    f = data["figures"]
    typer.echo(f"{f['flagged']} of {f['assessed']} agglomerations with a gap ({f['flagged_pe']:,} p.e.); "
               f"{f['poor']} poor bathing waters, {f['poor_with_upstream']} with a discharge upstream")
    typer.echo(f"{web.render(data)}\n{signals.write(data)}")


@app.command("all")
def run_all():
    """fetch, link and page."""
    fetch()
    link()
    page()


if __name__ == "__main__":
    app()
