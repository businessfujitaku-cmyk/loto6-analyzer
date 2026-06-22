"""Analyzer: compute per-number expectation scores (freq/gap/recent only).

Weights: freq=0.40, gap=0.40, recent=0.20
Level distribution (skewed toward top):
  Lv5=3, Lv4=6, Lv3=10, Lv2=11, Lv1=13  (total=43)
"""

from typing import List, Dict, Any

W_FREQ = 0.40
W_GAP = 0.40
W_RECENT = 0.20
RECENT_WINDOW = 50

LV_COUNTS = [3, 6, 10, 11, 13]  # Lv5, Lv4, Lv3, Lv2, Lv1


def _norm(val: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.5
    return (val - lo) / (hi - lo)


def compute(draws: List[Dict]) -> Dict[str, Any]:
    """Compute expectation scores for numbers 1-43.

    Returns:
        {
            "ready": bool,
            "total_draws": int,
            "items": [{ "number", "score", "level", "components": {freq, gap, recent} }],
            "summary": { odd_even_hist, consec_hist, sum_mean, sum_std }
        }
    """
    total = len(draws)
    if total < 10:
        return {"ready": False, "total_draws": total, "items": [], "summary": {}}

    # --- per-number statistics ---
    freq = {n: 0 for n in range(1, 44)}
    last_seen = {n: -1 for n in range(1, 44)}
    recent_count = {n: 0 for n in range(1, 44)}
    recent_start = max(0, total - RECENT_WINDOW)

    for i, d in enumerate(draws):
        for n in d["numbers"]:
            freq[n] += 1
            last_seen[n] = i
            if i >= recent_start:
                recent_count[n] += 1

    gap = {}
    for n in range(1, 44):
        if last_seen[n] < 0:
            gap[n] = total
        else:
            gap[n] = total - 1 - last_seen[n]

    # --- normalize ---
    freq_vals = list(freq.values())
    gap_vals = list(gap.values())
    recent_vals = list(recent_count.values())

    freq_lo, freq_hi = min(freq_vals), max(freq_vals)
    gap_lo, gap_hi = min(gap_vals), max(gap_vals)
    recent_lo, recent_hi = min(recent_vals), max(recent_vals)

    items = []
    for n in range(1, 44):
        nf = _norm(freq[n], freq_lo, freq_hi)
        ng = _norm(gap[n], gap_lo, gap_hi)
        nr = _norm(recent_count[n], recent_lo, recent_hi)
        score = W_FREQ * nf + W_GAP * ng + W_RECENT * nr
        score = max(0.0, min(1.0, score))
        items.append({
            "number": n,
            "score": round(score, 4),
            "level": 0,
            "components": {
                "freq": freq[n],
                "gap": gap[n],
                "recent": recent_count[n],
            },
        })

    # --- assign levels (skewed: Lv5=top3, Lv4=next6, ...) ---
    ranked = sorted(items, key=lambda x: x["score"], reverse=True)
    idx = 0
    for lv_idx, cnt in enumerate(LV_COUNTS):
        lv = 5 - lv_idx  # 5, 4, 3, 2, 1
        for _ in range(cnt):
            if idx < len(ranked):
                ranked[idx]["level"] = lv
                idx += 1

    items.sort(key=lambda x: x["number"])

    # --- summary for predictor ---
    import statistics
    sums = []
    odd_even_hist = {i: 0 for i in range(7)}
    consec_hist = {i: 0 for i in range(6)}

    for d in draws:
        nums = d["numbers"]
        s = sum(nums)
        sums.append(s)
        odds = sum(1 for x in nums if x % 2 == 1)
        odd_even_hist[odds] = odd_even_hist.get(odds, 0) + 1
        consec_pairs = sum(1 for j in range(len(nums) - 1) if nums[j + 1] - nums[j] == 1)
        consec_hist[min(consec_pairs, 5)] = consec_hist.get(min(consec_pairs, 5), 0) + 1

    summary = {
        "odd_even_hist": odd_even_hist,
        "consec_hist": consec_hist,
        "sum_mean": round(statistics.mean(sums), 2) if sums else 0,
        "sum_std": round(statistics.stdev(sums), 2) if len(sums) > 1 else 0,
    }

    return {
        "ready": True,
        "total_draws": total,
        "items": items,
        "summary": summary,
    }
