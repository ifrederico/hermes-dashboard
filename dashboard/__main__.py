"""Entry point for `python -m dashboard` and `hermes-dashboard` CLI."""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(
        prog="hermes-dashboard",
        description="Minimal read-only web dashboard for Hermes Agent",
    )
    parser.add_argument(
        "--port", type=int, default=9191, help="Port to listen on (default: 9191)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    args = parser.parse_args()

    print(f"\n  ☤ Hermes Dashboard")
    print(f"  → http://{args.host}:{args.port}\n")

    uvicorn.run(
        "dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
