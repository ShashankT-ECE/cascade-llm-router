# Cascade LLM Router & Cost Optimization Engine

A Monte Carlo simulation of a two-tier LLM routing system that demonstrates measurable API cost reduction without sacrificing output quality across a mixed-difficulty task workload.

---

## Section 1: Business Value

**Optimizing API spend via procedural fallback routing. Quantifies and optimizes reliability-cost tradeoffs.**

Routing every task to the most capable (and most expensive) model is the safe default — but it is rarely the optimal one. The majority of real-world coding tasks are low-to-medium complexity and can be solved reliably by a low-cost model. The Cascade Router exploits this skew: it attempts every task with the cheapest model first, and only escalates to the high-capability model when a failure is detected. The result is a dramatic reduction in per-task API spend while maintaining high overall success rates. For engineering teams running thousands of agentic tasks per day, this translates directly to reduced infrastructure budgets and faster iteration cycles.

---

## Section 2: Architecture

```
┌─────────────┐
│    Task     │
│   Input     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   Low-Cost Model    │  ($0.15 / 1M tokens)
│  (attempt first)    │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────┐
│  Procedural Evaluation   │  (test execution / probabilistic pass-fail)
│  Pass / Fail signal      │
└────┬─────────────────────┘
     │
     ├── PASS ──────────────────────────────────────► Final Output  ✓
     │
     └── FAIL
          │
          │  Log failure type
          │  (Logic Error / Edge Case / Syntax Violation)
          │
          ▼
┌──────────────────────────┐
│  High-Capability Model   │  ($15.00 / 1M tokens)
│     (fallback only)      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Procedural Evaluation   │
│  (second pass)           │
└────┬─────────────────────┘
     │
     ├── PASS ──────────────────────────────────────► Final Output  ✓
     │
     └── FAIL ─────────────────────────────────────► Task Failed   ✗
```

**Flow:** Task → Low-Cost Model → Procedural Evaluation → (If Fail) → Fallback High-Capability Model → Final Output

Verification is simulated probabilistically per task difficulty. In production this step would be replaced by live test execution or a lightweight evaluation model.

---

## Section 3: Assumptions & Modeling

This simulation models observed behavior across varying task complexities using a Monte Carlo approach over 1,000 tasks.

| Parameter              | Value                                      |
|------------------------|--------------------------------------------|
| Total tasks simulated  | 1,000                                      |
| Tokens per task        | 2,000                                      |
| Low-Cost price         | $0.15 / 1M tokens                          |
| High-Capability price  | $15.00 / 1M tokens                         |
| Difficulty distribution| 50% Easy, 30% Medium, 20% Hard             |
| Low-Cost pass rates    | Easy 85%, Medium 60%, Hard 20%             |
| High-Cap pass rates    | Easy 99%, Medium 90%, Hard 80%             |
| Fallback failure types | 50% Logic Error, 30% Edge Case, 20% Syntax |

Pass rates are calibrated to approximate real-world model behavior on code generation benchmarks. The difficulty distribution reflects a typical enterprise engineering workload skewed toward routine tasks.

---

## Section 4: System Limitations & Failure Modes

**Silent Failures (primary risk):** The most critical failure mode in this architecture is an imprecise verification layer. If the pass/fail signal is noisy — for example, a unit test suite with low coverage — a Low-Cost model output containing a subtle logic error may be accepted as passing. This is a "Silent Failure": incorrect code bypasses the expensive fallback entirely. In production, the quality of the verification step is the single largest determinant of system reliability.

**Hard task coverage gap:** Even with escalation, the High-Capability model fails on a non-trivial fraction of Hard tasks (simulated at 20%). The cascade system does not eliminate failure; it reduces unnecessary cost. Truly hard tasks may require human-in-the-loop review or domain-specific fine-tuning.

**Fixed token assumption:** This simulation assumes a uniform 2,000 tokens per task. Real workloads exhibit high variance. Tasks with longer prompts or larger outputs will shift actual costs upward and may alter the savings ratio.

**No latency modeling:** Fallback routing adds a second model call and increases end-to-end latency. For latency-sensitive pipelines this overhead may require architectural mitigation (e.g., parallel speculative execution).

**Static routing logic:** The simulator uses a fixed probabilistic threshold. A production router should adapt based on prompt features, historical accuracy per model, and task-type classification to improve routing precision over time.

---

## Section 5: Production Extensibility

This simulation framework can be extended to real API calls by replacing probabilistic evaluation with live model inference and test execution.

Concretely:
- Replace `random.random() < pass_rate` with an actual API call to the Low-Cost model and a test harness that returns pass/fail.
- The failure type classifier can be implemented as a lightweight secondary model or regex-based parser that inspects error output.
- The routing decision function is already isolated and can be wrapped around any async API client with minimal refactoring.
- Cost tracking, failure logging, and the Rich dashboard integrate directly with production observability stacks (Datadog, OpenTelemetry) by substituting the in-memory counters with metric emitters.

---

## Section 6: Key Insight

**The majority of cost savings are driven by high success rates on easy tasks, proving intelligent routing is most effective when workloads skew toward lower complexity.**

Easy tasks constitute 50% of the workload and the Low-Cost model handles 85% of them without escalation. This single segment contributes more to overall savings than all other segments combined. As workload complexity increases (more Hard tasks), the fallback trigger rate rises, high-capability model costs grow, and the savings margin compresses. The practical implication is that teams should invest in accurate task classification upfront: knowing that a task is "Easy" before routing it allows the system to commit confidently to the cheap path and maximise the cost delta between tiers.

---

## Section 7: Adversarial Stress Testing

The simulator includes a heavy-workload scenario — **80% Hard Tasks** (10% Easy, 10% Medium, 80% Hard) — to prove how the routing logic dynamically adjusts and degrades gracefully when core assumptions break.

Under this adversarial distribution, the Low-Cost model's aggregate pass rate collapses (Hard tasks pass at only 20%), causing the fallback trigger rate to spike dramatically. The High-Capability model absorbs the majority of tasks, and the cost savings margin compresses toward zero or beyond. This is the expected and correct behavior: the cascade system does not pretend to be cheap when the workload is genuinely hard. Instead it transparently reports the degradation, giving operators a data-driven signal to either reclassify workloads, adjust routing thresholds, or accept the cost increase as justified by task complexity.

The stress test output appears as a secondary dashboard at the end of each simulation run, enabling direct side-by-side comparison of savings percentage and fallback rate between normal and adversarial conditions.
