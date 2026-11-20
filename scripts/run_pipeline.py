"""Thin wrapper: run the full Northgate Maritime pipeline."""

from dat_gov.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["all"]))
