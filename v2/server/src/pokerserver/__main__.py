import argparse
import asyncio
import logging

from .config import Config
from .server import Server
from .web import Spectators


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
    parser.add_argument("--delay-ms", dest="action_delay_ms", type=int,
                        help="pause after each action so humans can watch")
    parser.add_argument("--web-port", type=int,
                        help="serve the live spectator page on this port")
    parser.add_argument("--web-host", default="127.0.0.1",
                        help="spectator page address (default: this machine "
                             "only; the page shows every hole card)")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--log-dir")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = vars(parser.parse_args())

    logging.basicConfig(
        level=logging.DEBUG if args.pop("verbose") else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = args.pop("port")
    web_port, web_host = args.pop("web_port"), args.pop("web_host")
    config = Config.load(args.pop("config"), **args)
    try:
        asyncio.run(run(config, port, web_host, web_port))
    except KeyboardInterrupt:
        pass


async def run(config: Config, port: int, web_host: str,
              web_port: int | None) -> None:
    spectators = None
    if web_port is not None:
        spectators = Spectators()
        await spectators.start(web_host, web_port)
        print(f"Spectator view: http://{'localhost' if web_host == '127.0.0.1' else web_host}"
              f":{spectators.port}/", flush=True)
    # With the web page on, matches start from its Start button instead of
    # automatically when the table fills or the lobby wait runs out.
    server = Server(config, port, spectators, manual_start=spectators is not None)
    if spectators:
        spectators.on_start = server.request_start
    await server.serve()


if __name__ == "__main__":
    main()
