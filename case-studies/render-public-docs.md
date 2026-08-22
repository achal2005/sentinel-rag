# From public docs to support evidence: Sentinel × Render

**Independent case study · 22 August 2026**

Sentinel is a local evidence-first support agent that routes questions, retrieves documentation, and returns cited answers or a human escalation. For this experiment, it answered five realistic, author-created cloud-platform tickets against eight hand-curated, attributed sections paraphrased from Render's public documentation. The initial configuration passed **2 of 5** strict deterministic cases; the combined prompt, output-parsing, and model configuration scored **5 of 5** on the same frozen tickets.

This is a small, auditable and rerunnable technical demonstration—not a claim about production readiness, a customer engagement, or Render's own support quality. It is not affiliated with or endorsed by Render.

## Why Render

Render is a close real-world analogue to Sentinel's fictional Meridian development corpus: a cloud application platform with documentation spanning deployments, services, databases, networking, domains, and operational troubleshooting. That makes a small Render-derived corpus a useful test of whether the existing support pipeline can move beyond its test fixture without application-specific code.

The test used five official documentation areas:

- [Custom domains](https://render.com/docs/custom-domains)
- [Health checks](https://render.com/docs/health-checks)
- [Environment variables](https://render.com/docs/configure-environment-variables)
- [Postgres recovery and backups](https://render.com/docs/postgresql-backups)
- [Regions](https://render.com/docs/regions)

## The question

Can Sentinel index a small, manually prepared corpus derived from a real company's public documentation, route realistic support questions through its application graph, retrieve the expected evidence, and keep citation IDs within retrieved and ticket-specific allowed source sets?

The acceptance bar was intentionally stricter than expected-source retrieval alone. A ticket passed only when all eight deterministic checks passed:

1. routed to the answer path;
2. answered without an unnecessary escalation;
3. retrieved the expected source;
4. cited the expected source;
5. used citation IDs drawn only from retrieved sources;
6. restricted citation IDs to the manually allowed source set for that ticket;
7. included every required answer concept; and
8. avoided any case-specific forbidden ambiguity found during reader review.

These checks measure explicit routing, retrieval, citation-ID, and phrase contracts. They do not prove logical entailment or replace a human support-quality review.

## Test design

I prepared eight short, attributed paraphrases from the five official pages, then indexed the resulting 13 chunks into a separate `sentinel_render_demo` database. The experiment did not crawl Render's website, and the normal Meridian knowledge base was left untouched.

The five tickets were frozen before comparison:

| Ticket | Support scenario | Core fact under test |
|---|---|---|
| RENDER-001 | Custom-domain verification with an AAAA record | Remove the AAAA record; verification is followed by managed TLS. |
| RENDER-002 | A new deploy fails its HTTP health check | A 2xx/3xx response within five seconds is healthy; an unhealthy replacement does not displace the working version. |
| RENDER-003 | Apply a new environment variable without rebuilding | Use **Save and deploy** to redeploy the existing build. |
| RENDER-004 | Restore a Hobby Postgres database to five days ago | Hobby has three days of PITR; upgrading today does not backfill older recovery history. |
| RENDER-005 | Move a service from Oregon to Frankfurt | Region cannot change in place; create and migrate to a new resource. |

Each ticket ran through Sentinel's `router → hybrid retrieval → cited answer` path. No answer was manually supplied, and the score was produced by deterministic checks over saved outputs. Runs were sequential and limited to six of the laptop's twelve logical CPUs to avoid sustained load.

## Baseline: the expected evidence was not enough

The Llama 3.2 3B baseline passed **2 of 5** cases.

| Metric | Baseline |
|---|---:|
| Strict ticket pass rate | **2 / 5 (40%)** |
| Expected source retrieved | **5 / 5** |
| Expected source cited | **5 / 5** |
| Citation IDs drawn only from retrieved sources | **5 / 5** |
| Citation IDs restricted to the allowed set | **2 / 5** |
| Required concepts present | **4 / 5** |
| Mean end-to-end latency | **9.8 s/ticket** |

This exposed two failure classes that a retrieval-only score would have missed:

- **Citation-set precision:** three responses cited IDs outside the manually allowed set even though the expected source was present.
- **Answer content:** the Postgres response omitted the three-day Hobby window and gave a misleading condition for whether upgrading would recover five-day-old history.

The baseline is preserved in [the generated report](../evals/reports/render_demo/latest.md), including every ticket, retrieved source, citation, answer, check, and duration.

## What changed

Three scoped changes were compared as a combined configuration:

1. **A stricter evidence prompt.** The answerer is told to use the smallest sufficient source set and cite only sources that directly support a claim.
2. **A hard output boundary.** Sentinel now stops at the first final `Sources:` line. This prevents model commentary after the answer from being interpreted as additional citations.
3. **A larger local answer model.** Llama 3.1 8B replaced Llama 3.2 3B for the comparison.

The corpus, tickets, and retrieval path stayed fixed. After generation, both saved runs were rescored with the same corrected deterministic rubric. A matcher was expanded to accept the Postgres wording “would not make the older restore available”; that saved answer was not regenerated or edited.

A fresh-reader review then caught a more important rubric blind spot in RENDER-002: an earlier answer used an `unless` conditional that could invert the documented health-check outcome. The case now explicitly rejects that wording, and only that ticket was rerun under the laptop-safe CPU limit. The final saved answer states directly that a healthy response is 2xx/3xx within five seconds and that Render will not replace the working version. This review is why the final case has eight checks rather than the original seven.

## Final result

The improved configuration passed **5 of 5** strict cases.

| Metric | Baseline 3B | Improved 8B | Change |
|---|---:|---:|---:|
| Strict ticket pass rate | 2 / 5 (40%) | **5 / 5 (100%)** | +60 percentage points |
| Expected source retrieved | 5 / 5 | **5 / 5** | no change |
| Expected source cited | 5 / 5 | **5 / 5** | no change |
| Citation IDs drawn only from retrieved sources | 5 / 5 | **5 / 5** | no change |
| Citation IDs restricted to allowed set | 2 / 5 | **5 / 5** | +3 tickets |
| Required concepts present | 4 / 5 | **5 / 5** | +1 ticket |
| Forbidden phrases absent | 5 / 5 | **5 / 5** | no change |
| Mean end-to-end latency | 9.8 s | **63.5 s** | 6.5× the mean latency |

The [final generated report](../evals/reports/render_demo_8b/latest.md) contains the complete evidence. Its saved per-ticket durations range from 52.8 to 98.1 seconds on this laptop.

## What the result means

The experiment supports a narrow but useful claim: Sentinel's routing, hybrid retrieval, and citation pipeline can answer against a small, manually prepared corpus derived from a real cloud platform's public documentation without Render-specific application logic, and the final configuration meets the defined deterministic contract on these five scenarios.

It also shows why a single “expected source retrieved” metric is weak. The baseline achieved 5/5 expected-source retrieval and kept all citation IDs inside the retrieved set, while only 2/5 responses passed the full contract. Allowed-source and answer-concept checks exposed failures that the retrieval metric hid.

The combined prompt, parsing, and model configuration improved the contract score but had 6.5 times the baseline mean latency. This experiment does not isolate the contribution of each change. For an interactive deployment, the next engineering decision would be to benchmark a faster hosted model or add a citation-selection step instead of assuming the 8B local setup is the final serving configuration.

## Limitations

- Five tickets are a demonstration set, not a statistically meaningful benchmark.
- The corpus is a curated, attributed, paraphrased snapshot of selected public pages—not Render's complete documentation.
- Deterministic phrase and source-ID checks do not prove logical entailment; the RENDER-002 reader-review finding demonstrates this limitation.
- No Render account, private data, production API, or live support workflow was accessed.
- Documentation can change after the verification date, so the source snapshot should be refreshed before rerunning this as a current benchmark.
- Latencies are descriptive measurements from one sequential run per saved ticket on one laptop, not a performance benchmark. Model digest, Ollama version, hardware profile, corpus hash, and commit SHA were not captured in these reports.

## Reproduce the evidence

The repository includes the [attributed Render corpus](../docs/targets/render), [five-case runner and rubric](../evals/targets/render_demo.py), [baseline report](../evals/reports/render_demo/latest.md), [final report](../evals/reports/render_demo_8b/latest.md), and [contract tests](../evals/tests/test_render_demo_contract.py).

Run the target-company contract tests:

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
backend/.venv/Scripts/python.exe -m pytest -q evals/tests/test_render_demo_contract.py
```

The live five-ticket run deliberately requires the isolated `sentinel_render_demo` database and `SUPPORT_PRODUCT_NAME=Render`; the runner refuses to use the default knowledge-base database. See `python -m evals.targets.render_demo --help` for the run and cooldown options.

## Evidence-mapped project bullets

- Retargeted an evidence-first support pipeline from a fictional corpus to eight attributed, hand-curated sections derived from Render documentation; the improved configuration passed **5/5** frozen scenarios under eight deterministic routing, retrieval, citation-ID, phrase-presence, and ambiguity checks.
- Diagnosed a **5/5 expected-source retrieval result versus 2/5 full-contract pass rate**, then compared a combined evidence-prompt, output-parsing, and model upgrade that reached **5/5**.
- Built an isolated evaluation database, attributed corpus, saved per-ticket artifacts, deterministic rescoring, reader-review regression check, and CI-runnable contract tests.
