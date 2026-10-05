# pokerserver

The table server for NUCATS Pokerbots v2. Bots connect over TCP using the protocol in [../docs/protocol.md](../docs/protocol.md).

## Run

```bash
cd v2/server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"

pokerserver --port 9000                        # defaults: 6 seats, 1000 chips, 10/20, 20 hands
pokerserver --port 9000 --config config.toml   # see config.example.toml
pokerserver --port 9000 --hands 20 --timeout-ms 5000 --lobby-wait 30 --seed 42
```

`--port` is required. There is no default and it can't be set in the config file.

A full table (6 bots) starts a match immediately. With 2 to 5 bots, the match starts once `lobby_wait_s` has passed. When the match ends, the server prints the leaderboard (rank, name, chips left, net), disconnects every bot and exits. To run several matches in a row, use `--matches N`, or `--matches 0` to keep going until Ctrl+C; bots that are still connected go back to the lobby between matches. Each match's hand history is written to `logs/<match_id>.jsonl`.

Players connect to `<this machine's LAN IP>:<port>`. Make sure the firewall allows incoming connections on that port.

## Test

```bash
pytest
```

The tests cover:

- `tests/test_engine.py`: poker rules (blinds, heads-up order, side and split pots, all-in runouts) plus 2,000 random hands checking that no chips are created or lost
- `tests/test_match.py`: full matches with in-memory bots, covering timeouts, illegal actions, disconnects, busting, standings and reproducible seeds
- `tests/test_server.py`: end-to-end tests over real TCP sockets, including every handshake and protocol error

## Layout

| File | What it does |
|---|---|
| `engine.py` | One hand of poker. Wraps PokerKit and turns its state into protocol events. No I/O. |
| `match.py` | One match: seating, button, hand loop, timeouts and defaults, standings, hand log |
| `server.py` | TCP listener, hello handshake, lobby, and running matches |
| `config.py` | Settings, loaded from TOML and command-line flags |
