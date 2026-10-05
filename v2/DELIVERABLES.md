# NUCATS Pokerbots v2: Deliverables

Status: **D1 (protocol spec) and D2 (table server, with D8 engine and server tests) are built.** See [docs/protocol.md](docs/protocol.md) and [server/](server/).

## Overview

One machine runs the **table server**. It is the single source of truth: it deals, enforces the rules, checks every action, and decides who wins. Players run their bots on their own machines, and each bot connects to the table server over **TCP**. The wire protocol is fully documented, so a bot can be written in any language.

```
 [Bot A] ─┐
 [Bot B] ─┤
 [Bot C] ─┼── TCP ──►  [Table server]  ── hand logs, results
 [Bot D] ─┤            (source of truth)
 [Bot E] ─┤
 [Bot F] ─┘
```

## Game format (decided)

| Setting | Value |
|---|---|
| Game | No-limit Texas Hold'em |
| Players per table | Up to 6 |
| Starting stack | 1000 chips |
| Blinds | 10 / 20 (small / big), fixed |
| Match length | 20 hands |
| Transport | TCP (moving away from WebSockets) |
| Protocol | Documented and language-agnostic |

## Confirmed design decisions

1. **Bots connect to us.** The table server listens on one port, and each bot opens a TCP connection to it. Players don't need a public address or open ports. Only the server does.
2. **Message framing is newline-delimited JSON.** Each message is one JSON object followed by `\n`. It's easy to handle in any language, and you can test by hand with `nc`.
3. **Stacks carry over between hands.** Chips won or lost stay with the player for all 20 hands. A player who runs out of chips is out for the rest of the match.
4. **The match ends after 20 hands, or earlier if only one player has chips left.** Players are ranked by final stack.
5. **The button moves one seat clockwise each hand.** Seats are assigned at random when the match starts.
6. **Each move has a time limit.** If the bot doesn't respond in time, the server checks for it if checking is allowed, otherwise folds.
7. **No API keys: identity is the TCP connection.** Each connection gets its own `player_id`. A dropped connection can't reclaim its seat: the seat stays in the match and the server plays it (check, or fold if it can't check).

Defaults chosen while building D1/D2. All can be changed in the config or spec:

- A full table starts at once. With 2 to 5 bots, the match starts after a 30 s lobby wait.
- Move timeout is 5 s per action. There is no time bank.
- An illegal action gets the default action. The bot doesn't get a second try.
- Equal final stacks share a rank. Busted players rank below everyone with chips, and busting later ranks higher.
- Cards shown at showdown are visible to everyone. Folded and mucked cards are never revealed.
- One table at a time. By default the server plays one match, prints the leaderboard, disconnects everyone and exits (`--matches N` plays more).
- Plain TCP for LAN play.

## Deliverables

### D1. Protocol specification (`v2/docs/protocol.md`)
This is the contract between the server and every bot, so it comes first and everything else follows it.

- Connection lifecycle: connect → `hello`/auth → wait in lobby → match → hands → match end → disconnect
- Every message type, with field names, types and an example
- What a bot sees on its turn:
  - its hole cards and the board
  - each seat's stack, current bet and status
  - pot size, the button and blind positions, and hand/street numbers
- Legal actions sent with every turn request: `fold`, `check`, `call` (with amount), `raise` (with min and max total)
- Public events broadcast to everyone: actions, new streets, showdown cards, and pot awards including side pots
- Errors: invalid action, bad message, timeout, auth failure. It must also say what the server does after each one.
- Card notation, e.g. `As`, `Td`, `2c`
- A protocol version number

**Done when:** someone who has never seen our code could write a working bot from the document alone.

### D2. Table server (`v2/server/`)
- TCP listener that handles many connections at once
- Handshake and session handling (one TCP connection = one bot identity)
- Lobby and seating: start a match with 2 to 6 bots
- Game engine: poker rules through **[PokerKit](https://github.com/uoftcprg/pokerkit)**, covering blinds, betting rounds, all-ins, side pots and showdowns. We don't write our own hand evaluator.
- Action checking: the server never trusts a bot. Anything malformed or illegal is rejected, and the bot gets the default action.
- Per-move timeouts and the default action
- Disconnects: the seat stays in the match and automatically checks or folds. Reconnecting gives a new identity.
- Port given on the command line (required). Configuration file covering the blinds, stacks, hand count, timeout and lobby wait

**Done when:** a 6-bot, 20-hand match runs from start to finish with no manual help, and the chip total stays at 6000 at the end of every hand.

### D3. Match logging and results (`v2/server/`)
- A full hand history for every match in a machine-readable format (JSON lines)
- Final standings: finishing position, final stack, and net chips won or lost
- Enough information in the logs to replay any hand exactly

**Done when:** any hand can be reconstructed from its log alone.

### D4. Reference Python SDK (`v2/sdk/python/`)
- Handles the connection, framing, login and reconnecting
- Callback-style bot class:
  ```python
  class MyBot(Bot):
      def get_action(self, state) -> Action: ...
      def on_hand_end(self, result): ...
  ```
- Typed state objects, plus card helpers

**Done when:** a bot written as just one `get_action` method can play a full match.

### D5. Sample bots (`v2/bots/`): beginner starter kit built: `my_bot.py` plus the `pokerbot/` helper package
- `random_bot`: picks a random legal action
- `call_bot`: always checks or calls
- `rule_bot`: a port of the v1 rule-based bot in [examples/sample_bot.py](../examples/sample_bot.py)
- A **bot in another language that uses no SDK** (e.g. a short Node or Go script), to prove the protocol works on its own

### D6. Local practice mode
- One command starts a server and fills the empty seats with sample bots, so a player can test their bot alone, e.g.:
  `python -m pokerserver practice --bot "python my_bot.py" --opponents 5`

### D7. Documentation (`v2/docs/`)
- `getting-started.md`: from nothing to a working bot in about 10 minutes
- `protocol.md` (D1)
- `rules.md`: game format, timeouts, the default action, how ranking works, and tie-breaks

### D8. Tests
- Engine checks: side pots, split pots, all-ins below the minimum raise, heads-up blind order, players who run out of chips
- Protocol checks: malformed messages, illegal actions, slow bots, sudden disconnects
- Long runs where many random bots play thousands of hands with no crashes and the chip total never changes

### D9. Spectator/admin view (spectator part built: `--web-port`; admin controls not yet)
- Live table view and leaderboard
- Admin controls to start, pause and remove bots

## Open questions

1. **Luck over 20 hands.** Only 20 hands of 6-handed poker leaves a lot to luck: each player gets roughly 3 hands on the button, and one big pot can decide the match. We could:
   - keep it as is, since it's fun and quick;
   - play several 20-hand matches and add up the results;
   - use **duplicate** dealing, where the same cards are dealt again with seats rotated, so card luck cancels out.
2. **Defaults to review:** time limit, tie-breaks, network, single table and what bots can see now have working defaults (listed under "Confirmed design decisions"). Change any you don't like.

## Suggested build order

1. D1 protocol spec, which we review together before writing any code
2. D2 server and D8 engine tests
3. D4 SDK and D5 sample bots
4. D6 practice mode and D3 logging
5. D7 docs
6. D9 spectator view, if there's time
