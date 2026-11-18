# btc-race-24h-20261118-1444

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/rfky18/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/rfky18/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A regime-aware hybrid paper-trading bot for cbBTC (Coinbase Wrapped BTC) on Solana — a make.fun bounty entry for **btc-race-24h-20261118-1444**: "Race a BTC trading bot live for 24 hours."

## Strategy: dip-bounce + trend confirmation (v-hybrid)

Patient dip-buying with a trend filter, built from evidence across four race windows:

- **Entry — dip-bounce:** price at least 130 bps below the 6-hour high, two consecutive green closes, RSI(14) at or below 40 (oversold, not catching a falling knife).
- **Entry — trend confirmation:** EMA60 slope over 30 bars at or above −5 bps (medium trend flat or up, not diving) and the 15-minute return at or above −30 bps (the slide has eased, not a sharp rally). This separates bounces in flat markets from dead-cat bounces mid-bleed.
- **Exit:** take profit 160 bps, stop loss 70 bps, trailing stop 80 bps (armed at +80 bps), time stop 6 hours.
- **Risk:** long only, one position at a time, at most 3 entries per window, no entry after bar 1380, cooldown 60 bars after a win / 120 after a loss, adaptive sizing (70% cash when 60-bar volatility exceeds 10 bps, 50% above 15 bps; halved again when price impact exceeds 25 bps).

## Local validation (honest numbers)

Graded with a local replay simulator implementing the official engine from the kit sources (fill at next bar's open, 4 bps fee, 2 bps slippage, constant-product impact). The simulator reproduces the official baselines exactly (buy-and-hold −$31.63, fee $0.79, max drawdown 3.25%).

| Window | Net PnL | Trades | Max DD |
|---|---|---|---|
| W0 dev (this contest, −2.80% grind down) | +$5.93 | 6 (3 round trips) | 1.51% |
| W1 0603-dev (+0.49% sideways) | +$22.54 | 5 | 0.94% |
| W2 0828-dev (−4.00% bleed + late rally) | −$6.24 | 2 | 0.72% |
| W3 2314-dev (−4.91% downtrend) | +$4.14 | 4 | 1.08% |

Win rate 67% on W0 (profit factor 1.57). No variant was positive on all four windows — the race window is an unseen regime, so this entry is a blind shot by design; the numbers above are local validation only, not a promise about the race.

For comparison, every official baseline failed the dev gate on W0: buy-and-hold −$31.63, hold-cash $0.00, momentum −$23.87, EMA-cross −$148.17, ADX-momentum −$75.57, RSI-Bollinger −$39.92.

## Run it

`main.py` is pure Python 3.13 standard library plus the vendored SDK shim in `vendor/` (byte-for-byte copy of the kit's `sdk/makefun_bars.py`). No network, no wall-clock, no randomness — the same input always produces identical orders.

```sh
node <kit>/cli/makefun.mjs grade-local --kit <kit> --bot . --driver docker
```

## Files

- `main.py` — the bot (protocol `agent-fun/bars-replay/v1`)
- `vendor/makefun_bars.py` — kit SDK shim (vendored, excluded from authorship)
- `LICENSE` — MIT

<sub>Entered on [make.fun](https://make.fun/?ref=2pd6m625&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
