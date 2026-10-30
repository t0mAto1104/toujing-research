# Company research workflow

## Evidence first

Set an explicit research cutoff in Beijing time, resolve issuer/security, and preserve the user's questions. Run collection once; inspect gaps and source dates. Use public filings as primary evidence and public financial APIs as structured inputs. Treat management statements and brokerage research as attributed views. Annual and quarterly disclosure titles alone do not establish that their content was read.

If an API fails, retain independent successful results. The seed collector includes a second Tencent K-line entry and an Eastmoney disclosure-list fallback; both can fail. It does not implement every upstream endpoint. Financial enhancement via Hithink is optional and uses the caller's key only. Do not bypass access controls or deploy another fetch service to evade restrictions.

Use the host's existing authorized search/browse tools to fill company identity, founding/listing and major developments; principal products, customers and revenue/profit composition; named competitors; official industry statistics (e.g. NBS); policy execution dates; ownership/control and actual risks. Publication date, observation period and retrieval time differ. Import source passages, not just links. Newly discovered official company URLs can be browsed by the host under its own safeguards; the bundled downloader only fetches fixed disclosure hosts.

## Shared analysis

Compute `workpaper.json`, then `plan.json`. Each role receives the same packet hash, security, cutoff, selected source passages and calculated values. Send only relevant passages/statistics, not every raw historical row to every role. All roles must use the same source ID namespace. Their output is saved separately:

| Role | Questions to answer | Artifact |
|---|---|---|
| Business/competition | What does the company sell, how does it earn money, what changed, who competes, why might its advantage fail? | business.json |
| Financial quality | What explains profit/cash change, which accounting facts qualify the result, what constrains liquidity/capital? | financial.json |
| Industry/policy | What do dated demand/supply/price/policy facts imply for this business, through what transmission? | industry.json |
| Valuation/risk | What assumptions sustain the current valuation; what measurable developments overturn the judgment? | valuation.json |

Run sequentially if the host cannot/should not delegate. Parallelism is an optimization, not a requirement or a guarantee of independent reasoning. No model is chosen or purchased by this skill.

## Review and supplement

Produce seven default modules, including synthesis. Review each role independently against actual evidence; do not let reviewers silently change raw data. Locate issues by JSON path, quote the disputed assertion, identify the source/period conflict and propose a correction. Distinguish actual contradiction from acquisition failure and not-applicable metrics.

Merge duplicate supplement requests across roles. One round, normally no more than two additional search calls. If a targeted public fetch is required, select it explicitly. Retain successful work and unresolved local limitations. Revise only affected claims. Synthesis must use the revised accepted facts and not restore rejected assertions.

Run `review`, fix mechanical errors, then conduct the semantic review in report-review.md. Report an actual company-specific judgment even when some independent modules are incomplete. Do not say a peer comparison failure invalidates company cash-flow evidence.

## Resume and cost boundaries

Save `evidence.json`, `workpaper.json`, `plan.json`, per-role drafts, `review.json`, and the final report in a per-task folder. Bind drafts/reviews to `packet_hash` and this skill version. If evidence changes, regenerate calculations and recheck dependent claims; never combine old source IDs with a new packet. The CLI checks evidence hashes when reviewing/rendering, but does not implement a background scheduler, role execution engine, lease or automatic replay. The host must inspect/reuse saved files deliberately.

No automatic paid request retry. Do not restart all four roles when one optional source or role fails. Upgrading the skill does not authorize regenerating old reports or uploading private documents. Long research may run in milestones; the seed collection has a configurable 10–600 second budget and 24-request ceiling, not an AI time limit. Stop on cancellation, exhausted user budget, credential/permission failures or diminishing evidence returns.
