import argparse
import asyncio
import logging

from .config import Config
from .server import Server


def main() -> None:
    parser = argparse.ArgumentParser(prog="pokerserver",
                                     description="NUCATS Pokerbots table server")
    parser.add_argument("--config", help="TOML config file")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int, required=True,
                        help="TCP port to listen on (required)")
    parser.add_argument("--hands", dest="hands_per_match", type=int)
    parser.add_argument("--timeout-ms", dest="action_timeout_ms", type=int)
    parser.add_argument("--lobby-wait", dest="lobby_wait_s", type=float)
    parser.add_argument("--matches", dest="max_matches", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--log-dir")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = vars(parser.parse_args())

    logging.basicConfig(
        level=logging.DEBUG if args.pop("verbose") else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = args.pop("port")
    config = Config.load(args.pop("config"), **args)
    try:
        asyncio.run(Server(config, port).serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
