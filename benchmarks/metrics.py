from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List


def aggregate_translation_rows(rows: Iterable[Dict[str, object]]) -> Dict[str, object]:
    rows_list: List[Dict[str, object]] = list(rows)
    total = len(rows_list)
    success = sum(1 for row in rows_list if not row.get("error"))

    validator_counts: Dict[str, Counter] = defaultdict(Counter)
    parsing_totals: Dict[str, float] = defaultdict(float)
    parsing_counts: Dict[str, int] = defaultdict(int)
    for row in rows_list:
        validators = row.get("validators") or {}
        for name, passed in validators.items():
            validator_counts[name]["passed" if passed else "failed"] += 1
        metrics = row.get("parsing_metrics") or {}
        for key, value in metrics.items():
            parsing_totals[key] += float(value)
            parsing_counts[key] += 1

    summary = {
        "total_sentences": total,
        "translations": success,
        "translation_rate": (success / total) if total else 0.0,
        "validators": {
            name: {
                "passed": counts.get("passed", 0),
                "failed": counts.get("failed", 0),
            }
            for name, counts in validator_counts.items()
        },
        "parsing_metrics": {
            key: (parsing_totals[key] / parsing_counts[key])
            for key in parsing_totals
            if parsing_counts[key]
        },
    }
    return summary


def aggregate_entailment_rows(rows: Iterable[Dict[str, object]]) -> Dict[str, object]:
    rows_list: List[Dict[str, object]] = list(rows)
    total = len(rows_list)
    correct = 0
    label_counts = Counter()
    for row in rows_list:
        pred = row.get("predicted_label")
        gold = row.get("label")
        if pred:
            label_counts[pred] += 1
        if pred and gold:
            if pred.lower() == str(gold).lower():
                correct += 1
    return {
        "total_examples": total,
        "predictions": sum(label_counts.values()),
        "accuracy": (correct / total) if total else 0.0,
        "label_distribution": dict(label_counts),
    }
