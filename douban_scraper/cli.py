"""Typer CLI interface for Douban scraper."""

import sys
import typer

from .core import collect_book_detail, collect_hot_catalog, collect_latest_catalog

app = typer.Typer(help="Douban catalog collector CLI")


@app.command("detail")
def book_detail(url: str = typer.Argument(..., help="Douban book subject URL to fetch")):
    """Fetch detailed information for a specific Douban book subject."""
    result = collect_book_detail(url)
    print(result.model_dump_json(indent=2))


@app.command("hot")
def hot_catalog():
    """Fetch Douban hot catalog books with pagination and output as JSON."""
    result = collect_hot_catalog()
    print(result.model_dump_json(indent=2))


@app.command("latest")
def latest_catalog():
    """Fetch Douban latest catalog books with pagination and output as JSON."""
    result = collect_latest_catalog()
    print(result.model_dump_json(indent=2))


def main(argv: list[str] | None = None) -> int:
    """Main entrypoint for CLI."""
    if argv is None:
        argv = sys.argv[1:]
    try:
        app(argv)
        return 0
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 0 if exc.code is None else 1


if __name__ == "__main__":
    sys.exit(main())
