"""Predictor: generate 5 diverse tickets using weighted sampling + fitness.

Fitness constraints (applied to 6-number combinations, NOT individual scores):
  - odd/even ratio alignment with historical mode
  - sum within mean +/- 1 std
  - consecutive pair count alignment
  - average individual score

Diversity: Jaccard similarity <= 0.4 between selected tickets.
"""

import random
import math
from typing import List, Dict, Any


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def generate(analysis: Dict[str, Any], n_tickets: int = 5, n_candidates: int = 6000) -> Dict[str, Any]:
    """Generate n_tickets diverse tickets from analysis result.

    Returns:
        {
            "ready": bool,
            "tickets": [{ "ticket", "numbers", "stats": {sum, odd, even, consec_pairs, avg_score} }],
            "note": str
        }
    """
    if not analysis.get("ready") or not analysis.get("items"):
        return {
            "ready": False,
            "tickets": [],
            "note": "データ同期前のため、ランダムに数字セットを生成しています。",
        }

    items = analysis["items"]
    summary = analysis.get("summary", {})
    score_map = {it["number"]: it["score"] for it in items}

    sum_mean = summary.get("sum_mean", 130)
    sum_std = summary.get("sum_std", 30)
    odd_even_hist = summary.get("odd_even_hist", {})
    consec_hist = summary.get("consec_hist", {})

    # find mode odd count
    mode_odd = 3
    if odd_even_hist:
        mode_odd = max(odd_even_hist, key=lambda k: odd_even_hist[k])
        if isinstance(mode_odd, str):
            mode_odd = int(mode_odd)

    mode_consec = 0
    if consec_hist:
        mode_consec = max(consec_hist, key=lambda k: consec_hist[k])
        if isinstance(mode_consec, str):
            mode_consec = int(mode_consec)

    # weighted sampling: score^1.5
    numbers = list(range(1, 44))
    weights = [max(score_map.get(n, 0.5), 0.01) ** 1.5 for n in numbers]
    total_w = sum(weights)
    weights = [w / total_w for w in weights]

    # generate candidates
    candidates = []
    for _ in range(n_candidates):
        chosen = set()
        attempts = 0
        while len(chosen) < 6 and attempts < 50:
            pick = random.choices(numbers, weights=weights, k=1)[0]
            chosen.add(pick)
            attempts += 1
        if len(chosen) == 6:
            combo = sorted(chosen)
            candidates.append(combo)

    # fitness scoring
    def _fitness(combo: List[int]) -> float:
        s = sum(combo)
        odds = sum(1 for x in combo if x % 2 == 1)
        consec = sum(1 for i in range(len(combo) - 1) if combo[i + 1] - combo[i] == 1)
        avg_sc = sum(score_map.get(n, 0.5) for n in combo) / 6

        # sum fitness: gaussian penalty
        if sum_std > 0:
            sum_fit = math.exp(-0.5 * ((s - sum_mean) / sum_std) ** 2)
        else:
            sum_fit = 1.0

        # odd/even: penalty for distance from mode
        odd_fit = max(0, 1.0 - abs(odds - mode_odd) * 0.25)

        # consecutive: penalty for distance from mode
        consec_fit = max(0, 1.0 - abs(consec - mode_consec) * 0.3)

        return 0.35 * avg_sc + 0.30 * sum_fit + 0.20 * odd_fit + 0.15 * consec_fit

    scored = [(c, _fitness(c)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    # greedy diversity selection
    selected = []
    for combo, fit in scored:
        combo_set = set(combo)
        if all(_jaccard(combo_set, set(s)) <= 0.4 for s in selected):
            selected.append(combo)
            if len(selected) >= n_tickets:
                break

    # fallback if not enough diverse tickets
    while len(selected) < n_tickets and scored:
        combo, _ = scored.pop(0)
        if combo not in selected:
            selected.append(combo)

    tickets = []
    for i, combo in enumerate(selected):
        s = sum(combo)
        odds = sum(1 for x in combo if x % 2 == 1)
        evens = 6 - odds
        consec = sum(1 for j in range(len(combo) - 1) if combo[j + 1] - combo[j] == 1)
        avg_sc = round(sum(score_map.get(n, 0.5) for n in combo) / 6, 3)
        tickets.append({
            "ticket": i + 1,
            "numbers": combo,
            "stats": {
                "sum": s,
                "odd": odds,
                "even": evens,
                "consec_pairs": consec,
                "avg_score": avg_sc,
            },
        })

    return {
        "ready": True,
        "tickets": tickets,
        "note": "",
    }
