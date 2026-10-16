"""Command line: fetch the reports, link discharges with bathing waters, render the pages and the signals.

Spain (docs/index.html, in Spanish) and France (docs/fr/index.html, in French) go through the same
commands; the signals of both countries share docs/signals.json."""
from __future__ import annotations

import typer

from . import analysis, analysis_fr, signals, web, web_fr
from .config import DATA_DIR
from .sources import baignade_fr, bathing, eru_fr, uwwtd
from .store import read_json, write_json

app = typer.Typer(add_completion=False, help="Depuración y baño: urban waste water and the bathing waters downstream.")
VERSIONS = DATA_DIR / "versions.json"


def _current() -> dict:
    """What the sources publish now: the date each country sent its UWWTD report, the latest bathing
    release, the latest ERU year of the French portal and the latest season of the French ministry."""
    rel = bathing.latest_release()
    res = baignade_fr.resources()
    season = baignade_fr.latest_season(res)
    return {"uwwtd": uwwtd.query_report()["version"], "bathing": f'{rel["season"]} v{rel["version"]} {rel["uuid"]}',
            "uwwtd_FR": uwwtd.query_report("FR")["version"], "eru_FR": eru_fr.latest_year(),
            "baignade_FR": f'{season} {max(r["last_modified"][:10] for r in res[season].values())}'}


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
    """Download the UWWTD tables, the bathing water classification and register, and the French sources."""
    for country in ("ES", "FR"):
        for name, n in uwwtd.fetch(country).items():
            typer.echo(f"uwwtd {country} {name}: {n}")
    rel = bathing.latest_release()
    rows = bathing.fetch_status(rel)
    for country in ("ES", "FR"):
        typer.echo(f"bathing {country} {rel['season']} v{rel['version']}: {rows[country]} rows, "
                   f"{bathing.fetch_zones(country)} registered bathing waters")
    typer.echo(f"ERU portal: {eru_fr.fetch()} plants of 2,000 p.e. or more")
    typer.echo(f"Ministry of Health: {baignade_fr.fetch()}")
    write_json(VERSIONS, _current())


@app.command()
def link():
    """Follow every discharge point downstream (HydroRIVERS) and write data/links.json and data/fr/links.json."""
    typer.echo(f"ES: {analysis.build_links()} discharge -> bathing water links")
    typer.echo(f"FR: {analysis_fr.build_links()} discharge -> bathing water links")


@app.command()
def page():
    """Render docs/index.html, docs/fr/index.html and docs/signals.json from the stored data."""
    data, fr = analysis.build(), analysis_fr.build()
    f = data["figures"]
    typer.echo(f"ES: {f['flagged']} of {f['assessed']} agglomerations with a gap ({f['flagged_pe']:,} p.e.); "
               f"{f['poor']} poor bathing waters, {f['poor_with_upstream']} with a discharge upstream")
    f = fr["figures"]
    typer.echo(f"FR: {f['noncompliant']} of {f['assessed']} agglomerations non-compliant "
               f"({f['noncompliant_pe']:,} p.e.); {f['poor']} poor bathing waters, "
               f"{f['poor_with_upstream']} with a discharge upstream")
    typer.echo(f"{web.render(data)}\n{web_fr.render(fr)}\n{signals.write(data, fr)}")


@app.command("all")
def run_all():
    """fetch, link and page."""
    fetch()
    link()
    page()


if __name__ == "__main__":
    app()
