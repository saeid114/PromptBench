"""
report_generator.py
Generate comparative reports from prompt strategy evaluations.
"""

import json
from typing import List, Dict
from pathlib import Path
from dataclasses import asdict

from scorers import ResponseEvaluation


def generate_comparison_report(
    evaluations: Dict[str, List[ResponseEvaluation]],
    output_dir: str = "outputs"
) -> str:
    """Generate a Markdown comparison report across prompt strategies."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# PromptBench — Strategy Comparison Report\n")

    # Collect all scenarios and strategies
    strategies = list(evaluations.keys())
    all_scenarios = set()
    for evals in evaluations.values():
        for e in evals:
            all_scenarios.add(e.scenario_id)
    scenarios = sorted(all_scenarios)

    # --- Overall Summary ---
    lines.append("## Overall Summary\n")
    lines.append("| Strategy | Avg Score | Best At | Weakest At |")
    lines.append("|----------|-----------|---------|------------|")

    strategy_avgs = {}
    for strat in strategies:
        evals = evaluations[strat]
        avg = sum(e.overall_score for e in evals) / len(evals) if evals else 0

        # Find best and worst dimensions
        dim_scores = {}
        for e in evals:
            for s in e.scores:
                dim_scores.setdefault(s.dimension, []).append(s.score)
        dim_avgs = {d: sum(sc) / len(sc) for d, sc in dim_scores.items()}
        best_dim = max(dim_avgs, key=dim_avgs.get) if dim_avgs else "N/A"
        worst_dim = min(dim_avgs, key=dim_avgs.get) if dim_avgs else "N/A"

        strategy_avgs[strat] = avg
        lines.append(f"| {strat} | **{avg:.1f}/10** | {best_dim} ({dim_avgs.get(best_dim, 0):.1f}) | {worst_dim} ({dim_avgs.get(worst_dim, 0):.1f}) |")

    # Winner
    winner = max(strategy_avgs, key=strategy_avgs.get)
    lines.append(f"\n**Overall Winner: `{winner}`** with {strategy_avgs[winner]:.1f}/10\n")

    # --- Per-Scenario Breakdown ---
    lines.append("\n## Per-Scenario Breakdown\n")

    for scenario_id in scenarios:
        lines.append(f"### Scenario: `{scenario_id}`\n")

        scenario_evals = {}
        for strat in strategies:
            for e in evaluations[strat]:
                if e.scenario_id == scenario_id:
                    scenario_evals[strat] = e

        if not scenario_evals:
            continue

        # Score comparison table
        dimensions = ["relevance", "clarity", "tone", "safety", "conciseness", "actionability"]
        header = "| Dimension | " + " | ".join(strategies) + " |"
        separator = "|-----------|" + "|".join(["-------"] * len(strategies)) + "|"
        lines.append(header)
        lines.append(separator)

        for dim in dimensions:
            row = f"| {dim.capitalize()} |"
            dim_scores = []
            for strat in strategies:
                e = scenario_evals.get(strat)
                if e:
                    dim_score = next((s.score for s in e.scores if s.dimension == dim), 0)
                    dim_scores.append((strat, dim_score))
                    row += f" {dim_score:.1f} |"
                else:
                    row += " — |"

            # Mark winner
            if dim_scores:
                best_strat = max(dim_scores, key=lambda x: x[1])
            lines.append(row)

        # Overall for this scenario
        overall_row = "| **Overall** |"
        scenario_scores = []
        for strat in strategies:
            e = scenario_evals.get(strat)
            if e:
                overall_row += f" **{e.overall_score:.1f}** |"
                scenario_scores.append((strat, e.overall_score))
            else:
                overall_row += " — |"
        lines.append(overall_row)

        if scenario_scores:
            best = max(scenario_scores, key=lambda x: x[1])
            lines.append(f"\n**Winner:** `{best[0]}` ({best[1]:.1f}/10)\n")

        # Key flags
        all_flags = []
        for strat, e in scenario_evals.items():
            for s in e.scores:
                for flag in s.flags:
                    all_flags.append(f"`{strat}`: {flag}")

        if all_flags:
            lines.append("**Flags:**")
            for flag in all_flags[:8]:
                lines.append(f"- {flag}")
            lines.append("")

        # Response previews
        lines.append("<details><summary>Response Previews</summary>\n")
        for strat, e in scenario_evals.items():
            lines.append(f"**{strat}** ({e.word_count} words):")
            lines.append(f"> {e.response_text[:300]}{'...' if len(e.response_text) > 300 else ''}\n")
        lines.append("</details>\n")

    # --- Dimension Rankings ---
    lines.append("\n## Dimension Rankings\n")
    lines.append("Which strategy performs best on each quality dimension:\n")

    for dim in dimensions:
        dim_by_strat = {}
        for strat, evals in evaluations.items():
            scores = [
                next((s.score for s in e.scores if s.dimension == dim), 0)
                for e in evals
            ]
            dim_by_strat[strat] = sum(scores) / len(scores) if scores else 0

        ranked = sorted(dim_by_strat.items(), key=lambda x: -x[1])
        rank_str = " > ".join(f"{s} ({v:.1f})" for s, v in ranked)
        lines.append(f"- **{dim.capitalize()}**: {rank_str}")

    report = "\n".join(lines)

    # Save report
    report_path = out / "comparison_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report saved to {report_path}")

    # Save raw scores as JSON
    scores_data = {}
    for strat, evals in evaluations.items():
        scores_data[strat] = []
        for e in evals:
            scores_data[strat].append({
                "scenario_id": e.scenario_id,
                "overall_score": e.overall_score,
                "word_count": e.word_count,
                "dimensions": {s.dimension: {"score": s.score, "flags": s.flags} for s in e.scores},
            })

    scores_path = out / "score_matrix.json"
    with open(scores_path, "w") as f:
        json.dump(scores_data, f, indent=2)
    print(f"Score matrix saved to {scores_path}")

    return report
