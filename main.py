"""v-hybrid: dip-bounce + konfirmasi tren (btc-race-24h-20261118-1444).

Dip-buy seperti v-dips (dip >= 130 bps vs high 6 jam + dua close hijau
+ RSI oversold), TAPI entry hanya kalau konfirmasi tren mengizinkan:
- SLOPE TIDAK DOWN: slope EMA60 per 30 bar >= -5 bps (tren menengah
  datar atau naik — bukan menukik).
- MOMENTUM PENDEK NAIK: return 15 menit >= +20 bps (pantulnya nyata,
  bukan satu bar hijau acak di tengah jatuh).

Tujuannya: memisahkan pantul di pasar datar (yang menang di W0/W1)
dari dead-cat bounce di tengah bleed (yang membunuh dip-buy di W2).
TP 160 / SL 70 / trailing 80 / time-stop 6 jam, max 3 entry,
cooldown 60/120, sizing adaptif.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYM = "CBBTC"

USE_RSI = True
USE_BLEED = False         # (tidak dipakai; slope + momentum pendek jadi filter)
USE_SLOPE = True          # syarat slope EMA60/30 bar >= -5 bps
USE_TP_SL = True
USE_ADAPTIVE_SIZE = True

DIP_WIN = 360
DIP_BPS = 130
RSI_MAX = 40
SLOPE_MIN_BPS = -5
ROC15_MIN_BPS = -30         # (diperbaiki dari +20: pantul 2 bar tidak mungkin
                            # menghasilkan +20 bps/15 mnt setelah dip 130 bps —
                            # ret15 di semua event dip nyata adalah NEGATIF.
                            # -30 bps berarti slide 15 menit sudah mereda,
                            # bukan rally tajam; memblokir slide tercuram.)
TP_BPS = 160
SL_BPS = 70
TRAIL_ARM_BPS = 80
TRAIL_BPS = 80
TIME_STOP = 360
MAX_ENTRIES = 3
COOLDOWN_WIN = 60
COOLDOWN_LOSS = 120
NO_ENTRY_AFTER_SEQ = 1380
MAX_SLIPPAGE_BPS = 500

closes = []
highs = []
lows = []
ema60 = None
ema60_hist = []
entries = 0
cooldown_until = -1
peak = None
_entry_seq = [-1]


def bps(a, b):
    return (a - b) * 10000 // b if b else 0


def ema_step(prev, x, n):
    if prev is None:
        return float(x)
    alpha = 2.0 / (n + 1.0)
    return prev + alpha * (x - prev)


def rsi14():
    if len(closes) < 15:
        return 50.0
    gains = 0.0
    losses = 0.0
    for j in range(len(closes) - 14, len(closes)):
        d = closes[j] - closes[j - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if losses == 0:
        return 100.0
    if gains == 0:
        return 0.0
    return 100.0 - 100.0 / (1.0 + (gains / 14.0) / (losses / 14.0))


def vol60_bps():
    if len(closes) < 61:
        return 0.0
    rets = []
    for j in range(len(closes) - 60, len(closes)):
        rets.append((closes[j] - closes[j - 1]) * 10000.0 / closes[j - 1])
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return math.sqrt(var)


def entry_price(state, holding):
    sym = state.hello["symbols"][0]
    return holding.cost * 10 ** (sym["qty_scale"] + sym["price_scale"]) // (
        holding.qty * 10 ** state.hello["capital"]["quote_scale"])


def on_batch(state, batch):
    global entries, cooldown_until, peak, ema60
    bar = state.latest.get(SYM)
    if bar is None:
        return []
    c = int(bar["c"])
    closes.append(c)
    highs.append(int(bar["h"]))
    lows.append(int(bar["l"]))
    ema60 = ema_step(ema60, c, 60)
    ema60_hist.append(ema60)

    for f in batch.get("fills", []):
        if f.get("side") == "buy" and f.get("status") == "filled":
            entries += 1

    holding = state.positions.get(SYM)
    if holding is not None:
        ep = entry_price(state, holding)
        ret = bps(c, ep)
        if peak is None or c > peak:
            peak = c
        do_exit = False
        if USE_TP_SL:
            trail_ret = bps(c, peak)
            peak_ret = bps(peak, ep)
            if ret >= TP_BPS or ret <= -SL_BPS:
                do_exit = True
            elif peak_ret >= TRAIL_ARM_BPS and trail_ret <= -TRAIL_BPS:
                do_exit = True
        if state.seq - _entry_seq[0] >= TIME_STOP:
            do_exit = True
        if do_exit:
            cooldown_until = state.seq + (COOLDOWN_LOSS if ret < 0 else COOLDOWN_WIN)
            peak = None
            return [{"side": "sell", "symbol": SYM, "qty": holding.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    peak = None
    if state.warming_up:
        return []
    if len(closes) < DIP_WIN + 1:
        return []
    if state.seq > NO_ENTRY_AFTER_SEQ:
        return []
    if entries >= MAX_ENTRIES:
        return []
    if state.seq <= cooldown_until:
        return []

    hi = max(highs[-DIP_WIN:])
    if bps(hi, c) < DIP_BPS:
        return []
    if not (c > closes[-2] and closes[-2] > closes[-3]):
        return []
    if USE_RSI and rsi14() > RSI_MAX:
        return []
    # konfirmasi tren: slope EMA60 tidak DOWN + momentum 15 menit naik
    if USE_SLOPE and len(ema60_hist) >= 31:
        slope = (ema60_hist[-1] - ema60_hist[-31]) * 10000.0 / ema60_hist[-31]
        if slope < SLOPE_MIN_BPS:
            return []
    if bps(c, closes[-16]) < ROC15_MIN_BPS:
        return []

    frac = 100
    if USE_ADAPTIVE_SIZE:
        v = vol60_bps()
        if v > 15:
            frac = 50
        elif v > 10:
            frac = 70
    amount = state.cash * frac // 100
    room = state.weight_room(SYM)
    if room < amount:
        amount = room
    impact = state.impact_bps(SYM, amount)
    if impact is not None and impact > 25:
        amount = amount // 2
    if amount < int(state.hello["fees"]["min_notional_quote_units"]):
        return []
    _entry_seq[0] = state.seq
    return [{"side": "buy", "symbol": SYM, "notional_quote_units": amount,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


makefun_bars.run(on_batch)
