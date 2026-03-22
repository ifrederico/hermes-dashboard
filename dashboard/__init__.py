"""Hermes Dashboard — minimal read-only web UI for Hermes Agent."""

__version__ = "0.1.0"


def main():
    """CLI entry point: hermes-dashboard [--port PORT] [--host HOST]."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Hermes Dashboard")
    parser.add_argument("--port", type=int, default=9191, help="Port (default: 9191)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host (default: 127.0.0.1)")
    args = parser.parse_args()

    print(f"☤ Hermes Dashboard → http://{args.host}:{args.port}")
    uvicorn.run("dashboard.app:app", host=args.host, port=args.port, log_level="warning")
