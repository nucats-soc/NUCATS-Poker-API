"""
Sample bot for the NUCATS Pokerbots v2 server (protocol v1).

Standard library only. Copy it, then change decide() to build your own bot.

Usage:
    python sample_bot.py --host 127.0.0.1 --port 9000
    python sample_bot.py --port 9000 --count 4      # run 4 copies, handy for testing
"""
import argparse
import json
import random
import socket
import threading
from collections import Counter

RANKS = "23456789TJQKA"


# --------------------------------------------------------------- strategy

def rank(card: str) -> int:
    return RANKS.index(card[0])        # 0 = Two ... 12 = Ace


def has_straight(ranks: set[int]) -> bool:
    if 12 in ranks:
        ranks = ranks | {-1}           # ace plays low in A-2-3-4-5
    return any(all(r + i in ranks for i in range(5)) for r in range(-1, 9))


def hand_strength(hole: list[str], board: list[str]) -> float:
    """Rough 0-1 score for the best hand visible from hole cards + board."""
    cards = hole + board
    ranks = [rank(c) for c in cards]
    counts = sorted(Counter(ranks).values(), reverse=True)
    flush = max(Counter(c[1] for c in cards).values()) >= 5
    straight = has_straight(set(ranks))
    high = max(rank(c) for c in hole) / 12

    if flush and straight:
        return 1.0
    if counts[0] == 4:
        return 0.95
    if counts[0] == 3 and len(counts) > 1 and counts[1] >= 2:
        return 0.9
    if flush:
        return 0.85
    if straight:
        return 0.8
    if counts[0] == 3:
        return 0.7
    if counts[0] == 2 and len(counts) > 1 and counts[1] == 2:
        return 0.6
    if counts[0] == 2:
        return 0.4 + 0.1 * high

    # Nothing made yet: judge the hole cards (both of them)
    low = min(rank(c) for c in hole) / 12
    score = 0.1 + 0.15 * high + 0.1 * low
    if hole[0][1] == hole[1][1]:
        score += 0.05                  # suited
    if abs(rank(hole[0]) - rank(hole[1])) == 1:
        score += 0.05                  # connected
    return score


def decide(req: dict, rng: random.Random) -> dict:
    """Given an action_request, return {'action': ..., 'amount': ...}."""
    legal = req["legal_actions"]
    strength = hand_strength(req["hole_cards"], req["board"])
    to_call = legal["call"] or 0
    pot_odds = to_call / (req["pot"] + to_call) if to_call else 0

    # Strong hand: raise between 2x and 4x the minimum, within what's allowed.
    # Before the flop a good pair (99+) is already worth a raise.
    raise_at = 0.45 if req["street"] == "preflop" else 0.7
    if strength >= raise_at and legal["raise"]:
        lo, hi = legal["raise"]["min"], legal["raise"]["max"]
        return {"action": "raise", "amount": min(hi, lo * rng.randint(2, 4))}

    if legal["check"]:
        return {"action": "check"}

    # Call when the hand is decent, or the price is cheap relative to the pot
    if strength >= 0.3 or pot_odds <= 0.2:
        return {"action": "call"}

    return {"action": "fold"}


# ----------------------------------------------------------------- client

def play(host: str, port: int, name: str, verbose: bool, seed: int) -> None:
    rng = random.Random(seed)
    log = (lambda *a: print(f"[{name}]", *a, flush=True)) if verbose else (lambda *a: None)

    sock = socket.create_connection((host, port))
    f = sock.makefile("rw", encoding="utf-8")

    def send(msg: dict) -> None:
        f.write(json.dumps(msg) + "\n")
        f.flush()

    send({"type": "hello", "protocol": 1, "name": name})
    seat = None

    for line in f:
        msg = json.loads(line)
        kind = msg["type"]

        if kind == "welcome":
            log(f"connected as {msg['player_id']}, waiting for a match...")
        elif kind == "match_start":
            seat = msg["your_seat"]
            log(f"match {msg['match_id']} started, I'm in seat {seat} "
                f"with {len(msg['seats'])} players")
        elif kind == "hand_start":
            log(f"hand {msg['hand_number']}: dealt {' '.join(msg['hole_cards']) or '(out)'}")
        elif kind == "action_request":
            choice = decide(msg, rng)
            send({"type": "action", "request_id": msg["request_id"], **choice})
            log(f"  {msg['street']:7} board [{' '.join(msg['board'])}] pot {msg['pot']}"
                f" -> {choice['action']} {choice.get('amount', '')}")
        elif kind == "hand_end":
            me = next((r for r in msg["results"] if r["seat"] == seat), None)
            if me:
                log(f"  result: {me['net']:+d}, stack {me['stack']}")
        elif kind == "match_end":
            log("match over:")
            for s in msg["standings"]:
                log(f"  #{s['rank']} {s['name']:12} {s['stack']:5} ({s['net']:+d})")
        elif kind == "error":
            log(f"  server error: {msg['code']}: {msg['message']}")

    log("disconnected")


def main() -> None:
    parser = argparse.ArgumentParser(description="NUCATS v2 sample poker bot")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--name", default="SampleBot")
    parser.add_argument("--count", type=int, default=1,
                        help="run this many copies at once (for testing)")
    parser.add_argument("--quiet", action="store_true",
                        help="with --count, only the first bot prints")
    args = parser.parse_args()

    threads = []
    for i in range(args.count):
        name = args.name if args.count == 1 else f"{args.name}{i + 1}"
        verbose = not args.quiet or i == 0
        t = threading.Thread(target=play, daemon=True,
                             args=(args.host, args.port, name, verbose, i))
        t.start()
        threads.append(t)
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
