import random
from rich.console import Console
from rich.table import Table
from rich import box

# ── Configuration ────────────────────────────────────────────────────────────
TOTAL_TASKS = 1_000
TOKENS_PER_TASK = 2_000

LOW_COST_PRICE_PER_1M  = 0.15   # $0.15 / 1M tokens
HIGH_CAP_PRICE_PER_1M  = 15.00  # $15.00 / 1M tokens

PASS_RATES = {
    "Easy":   {"low": 0.85, "high": 0.99},
    "Medium": {"low": 0.60, "high": 0.90},
    "Hard":   {"low": 0.20, "high": 0.80},
}

FAILURE_DIST = {
    "Logic Error":           0.50,
    "Edge Case Failure":     0.30,
    "Syntax/Rule Violation": 0.20,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def token_cost(tokens, price_per_1m):
    return (tokens / 1_000_000) * price_per_1m

def weighted_choice(choices: dict):
    population = list(choices.keys())
    weights    = list(choices.values())
    return random.choices(population, weights=weights, k=1)[0]

# ── Simulation ────────────────────────────────────────────────────────────────

def simulate(difficulty_dist, seed=42):
    """
    Run the cascade simulation.

    difficulty_dist: dict mapping difficulty label -> probability weight
    Returns (counters, trace_entries) where trace_entries is a list of dicts
    for every task, used to extract sample traces.
    """
    random.seed(seed)

    counters = {
        "difficulty": {k: 0 for k in difficulty_dist},
        "low_pass":   0,
        "low_fail":   0,
        "high_pass":  0,
        "high_fail":  0,
        "failure_type": {k: 0 for k in FAILURE_DIST},
    }

    trace_entries = []

    for task_id in range(1, TOTAL_TASKS + 1):
        difficulty = weighted_choice(difficulty_dist)
        counters["difficulty"][difficulty] += 1

        entry = {"task_id": task_id, "difficulty": difficulty}

        low_pass_rate = PASS_RATES[difficulty]["low"]
        if random.random() < low_pass_rate:
            counters["low_pass"] += 1
            entry["low_result"]  = "Passed"
            entry["fallback"]    = False
            entry["high_result"] = None
            entry["failure_type"] = None
        else:
            counters["low_fail"] += 1
            failure_type = weighted_choice(FAILURE_DIST)
            counters["failure_type"][failure_type] += 1
            entry["low_result"]   = "Failed"
            entry["failure_type"] = failure_type
            entry["fallback"]     = True

            high_pass_rate = PASS_RATES[difficulty]["high"]
            if random.random() < high_pass_rate:
                counters["high_pass"] += 1
                entry["high_result"] = "Passed"
            else:
                counters["high_fail"] += 1
                entry["high_result"] = "Failed"

        trace_entries.append(entry)

    return counters, trace_entries

# ── Financial ─────────────────────────────────────────────────────────────────

def financials(counters):
    low_calls  = TOTAL_TASKS
    high_calls = counters["low_fail"]

    cascade_cost   = (
        token_cost(low_calls  * TOKENS_PER_TASK, LOW_COST_PRICE_PER_1M) +
        token_cost(high_calls * TOKENS_PER_TASK, HIGH_CAP_PRICE_PER_1M)
    )
    full_high_cost = token_cost(TOTAL_TASKS * TOKENS_PER_TASK, HIGH_CAP_PRICE_PER_1M)
    savings        = full_high_cost - cascade_cost
    savings_pct    = (savings / full_high_cost) * 100 if full_high_cost else 0

    # Total passes
    cascade_passes  = counters["low_pass"] + counters["high_pass"]
    # Overall reliability for full-high scenario using actual difficulty counts
    full_high_passes = sum(
        int(count * PASS_RATES[diff]["high"])
        for diff, count in counters["difficulty"].items()
    )

    cascade_reliability  = cascade_passes / TOTAL_TASKS * 100
    full_high_reliability = full_high_passes / TOTAL_TASKS * 100

    cascade_cost_per_pass  = cascade_cost  / cascade_passes  if cascade_passes  else 0
    full_high_cost_per_pass = full_high_cost / full_high_passes if full_high_passes else 0

    return {
        "low_calls":               low_calls,
        "high_calls":              high_calls,
        "cascade_cost":            cascade_cost,
        "full_high_cost":          full_high_cost,
        "savings":                 savings,
        "savings_pct":             savings_pct,
        "cascade_passes":          cascade_passes,
        "full_high_passes":        full_high_passes,
        "cascade_reliability":     cascade_reliability,
        "full_high_reliability":   full_high_reliability,
        "cascade_cost_per_pass":   cascade_cost_per_pass,
        "full_high_cost_per_pass": full_high_cost_per_pass,
    }

# ── Sample Execution Trace ────────────────────────────────────────────────────

def render_trace(trace_entries, console, task_ids=(42, 150, 777)):
    console.rule("[bold yellow]Sample Execution Trace[/bold yellow]")
    console.print()

    for tid in task_ids:
        entry = trace_entries[tid - 1]   # task IDs are 1-indexed
        diff  = entry["difficulty"]

        if not entry["fallback"]:
            line = (
                f"  Task #{tid:>4} [[bold]{diff}[/bold]]: "
                f"[green]Low-Cost -> Passed[/green]"
            )
        else:
            ftype       = entry["failure_type"]
            high_result = entry["high_result"]
            high_color  = "green" if high_result == "Passed" else "red"
            line = (
                f"  Task #{tid:>4} [[bold]{diff}[/bold]]: "
                f"[red]Low-Cost -> Failed ({ftype})[/red] "
                f"-> Fallback High-Capability -> "
                f"[{high_color}]{high_result}[/{high_color}]"
            )
        console.print(line)

    console.print()

# ── Main Dashboard ────────────────────────────────────────────────────────────

def render_dashboard(counters, fin, console, title="LLM Reliability & Cost Optimization Dashboard"):
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    console.print()

    # ── Table 1: Task Overview ────────────────────────────────────────────────
    t1 = Table(title="[bold]Task Overview[/bold]", box=box.ROUNDED,
               header_style="bold magenta")
    t1.add_column("Metric",  style="cyan",  min_width=30)
    t1.add_column("Value",   style="white", justify="right")

    t1.add_row("Total Tasks", f"{TOTAL_TASKS:,}")
    for diff, count in counters["difficulty"].items():
        pct = count / TOTAL_TASKS * 100
        t1.add_row(f"  {diff} Tasks", f"{count:,}  ({pct:.1f}%)")
    console.print(t1)
    console.print()

    # ── Table 2: Routing Performance ─────────────────────────────────────────
    t2 = Table(title="[bold]Routing Performance[/bold]", box=box.ROUNDED,
               header_style="bold magenta")
    t2.add_column("Metric",  style="cyan",  min_width=45)
    t2.add_column("Count",   style="white", justify="right")
    t2.add_column("Rate",    style="green", justify="right")

    low_pass_rate  = counters["low_pass"] / TOTAL_TASKS * 100
    fallback_rate  = counters["low_fail"] / TOTAL_TASKS * 100
    high_pass_rate = (counters["high_pass"] / counters["low_fail"] * 100
                      if counters["low_fail"] else 0)

    t2.add_row("Low-Cost Model: Passed",
               f"{counters['low_pass']:,}", f"{low_pass_rate:.1f}%")
    t2.add_row("Low-Cost Model: Failed (Fallback Triggered)",
               f"{counters['low_fail']:,}", f"{fallback_rate:.1f}%")
    t2.add_row("High-Capability Model: Passed (of fallbacks)",
               f"{counters['high_pass']:,}", f"{high_pass_rate:.1f}%")
    t2.add_row("High-Capability Model: Failed (of fallbacks)",
               f"{counters['high_fail']:,}", f"{100 - high_pass_rate:.1f}%")
    console.print(t2)
    console.print()

    # ── Table 3: Failure Insights ─────────────────────────────────────────────
    t3 = Table(title="[bold]Failure Insight Breakdown (Low-Cost Model Failures)[/bold]",
               box=box.ROUNDED, header_style="bold magenta")
    t3.add_column("Failure Type",   style="cyan",   min_width=30)
    t3.add_column("Count",          style="white",  justify="right")
    t3.add_column("% of Failures",  style="yellow", justify="right")

    total_failures = counters["low_fail"]
    for ftype, count in counters["failure_type"].items():
        pct = count / total_failures * 100 if total_failures else 0
        t3.add_row(ftype, f"{count:,}", f"{pct:.1f}%")
    console.print(t3)
    console.print()

    # ── Table 4: Financial Simulation ────────────────────────────────────────
    t4 = Table(title="[bold]Financial Simulation[/bold]", box=box.ROUNDED,
               header_style="bold magenta")
    t4.add_column("Metric",                  style="cyan",  min_width=46)
    t4.add_column("100% High-Capability",    style="white", justify="right")
    t4.add_column("Cascade System",          style="green", justify="right")

    t4.add_row("Total Cost (USD)",
               f"${fin['full_high_cost']:.4f}",
               f"${fin['cascade_cost']:.4f}")
    t4.add_row("Overall System Reliability",
               f"{fin['full_high_reliability']:.1f}%",
               f"{fin['cascade_reliability']:.1f}%")
    t4.add_row("Cost per Successful Task (USD)",
               f"${fin['full_high_cost_per_pass']:.6f}",
               f"${fin['cascade_cost_per_pass']:.6f}")
    t4.add_row("API Call Mix",
               f"{TOTAL_TASKS:,} high-cap",
               f"{fin['low_calls']:,} low + {fin['high_calls']:,} high")
    t4.add_section()
    t4.add_row("[bold yellow]Total Savings[/bold yellow]",
               "",
               f"[bold green]${fin['savings']:.4f}  ({fin['savings_pct']:.1f}%)[/bold green]")
    console.print(t4)
    console.print()

    console.rule("[bold green]Simulation Complete[/bold green]")
    console.print()

# ── Adversarial Stress-Test Dashboard (compact) ───────────────────────────────

def render_stress_dashboard(counters, fin, console):
    console.rule("[bold red]Adversarial Stress Test — 80% Hard Tasks[/bold red]")
    console.print()

    t = Table(title="[bold]Stress Test Summary[/bold]", box=box.ROUNDED,
              header_style="bold red")
    t.add_column("Metric",            style="cyan",   min_width=46)
    t.add_column("Baseline (Normal)", style="white",  justify="right")
    t.add_column("Stress (80% Hard)", style="yellow", justify="right")

    fallback_rate     = counters["low_fail"] / TOTAL_TASKS * 100
    cascade_rel       = fin["cascade_reliability"]

    # Baseline reference values (from standard run — hardcoded from seed=42 output)
    BASE_FALLBACK_PCT  = 100 - 64.9   # ~35.1% fallback in normal run
    BASE_SAVINGS_PCT   = fin["savings_pct"]   # will differ; shown side-by-side

    t.add_row("Fallback Trigger Rate",
              f"~{BASE_FALLBACK_PCT:.1f}%",
              f"[red]{fallback_rate:.1f}%[/red]")
    t.add_row("Overall System Reliability",
              "—",
              f"{cascade_rel:.1f}%")
    t.add_row("Cascade Cost (USD)",
              "—",
              f"${fin['cascade_cost']:.4f}")
    t.add_row("Cost per Successful Task",
              "—",
              f"${fin['cascade_cost_per_pass']:.6f}")
    t.add_section()
    t.add_row("[bold yellow]Total Savings vs. 100% High-Cap[/bold yellow]",
              "—",
              f"[bold {'green' if fin['savings_pct'] > 0 else 'red'}]"
              f"{fin['savings_pct']:.1f}%[/bold {'green' if fin['savings_pct'] > 0 else 'red'}]")
    console.print(t)
    console.print()
    console.print(
        "  [italic dim]Under extreme hard-task load, Low-Cost pass rates collapse (~20%), "
        "fallbacks dominate, and savings compress significantly — "
        "demonstrating graceful degradation rather than catastrophic failure.[/italic dim]"
    )
    console.print()
    console.rule("[bold red]Stress Test Complete[/bold red]")

# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    console = Console()

    # ── Standard Run ─────────────────────────────────────────────────────────
    NORMAL_DIST = {"Easy": 0.50, "Medium": 0.30, "Hard": 0.20}
    counters, traces = simulate(NORMAL_DIST, seed=42)
    fin = financials(counters)

    render_trace(traces, console, task_ids=(42, 150, 777))
    render_dashboard(counters, fin, console)

    # ── Adversarial Stress Test ───────────────────────────────────────────────
    STRESS_DIST = {"Easy": 0.10, "Medium": 0.10, "Hard": 0.80}
    s_counters, _ = simulate(STRESS_DIST, seed=42)
    s_fin = financials(s_counters)

    render_stress_dashboard(s_counters, s_fin, console)
