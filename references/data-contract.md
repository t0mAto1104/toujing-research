# Data contracts · schema 1

All JSON is UTF-8, finite numbers only. Missing values are `null` or absent, never a default zero. Files containing private evidence belong outside the skill checkout. The CLI packet is intentionally portable and does not import the website's D1, React or Worker modules.

## Evidence packet

`collect` creates:

```json
{
  "schema_version": 1,
  "security": {"code":"600519","exchange":"SH","symbol":"sh600519","id":"600519.SH","asset":"A-share company"},
  "as_of": "2026-10-30",
  "created_at": "2026-10-30T01:00:00+00:00",
  "sources": [],
  "observations": [],
  "documents": [],
  "statements": [],
  "gaps": [],
  "untrusted_content": true
}
```

Each source has `id`, `title`, HTTPS `url`, `kind`, `fetched_at` and `trust`. Optional `published_at`, `source_time`, `stale`, `read_status`, `identity_status` explain actual coverage; a missing publication date is not substituted with retrieval date. IDs are packet-local. Same URL reuses an ID; preserve its reading/version metadata. Do not merge source namespaces from independent packets by concatenating files.

A financial row contains:

```json
{
  "security":"600519.SH",
  "period":"2025-12-31",
  "published_at":"2026-04-01",
  "statement":"lrb",
  "currency":"CNY",
  "unit":"元",
  "scope":"consolidated",
  "basis":"ytd",
  "source_id":"S1",
  "values":{"营业收入":1000000,"归属于母公司所有者的净利润":100000},
  "field_origins":{}
}
```

**The numbers above illustrate a schema, not real company data.** Supported statement types: `lrb`, `fzb`, `llb`; `fzb` requires `balance`, others require `ytd`. Use `parent` or `unknown` scope if consolidation is unverified; such rows do not enter consolidated calculations. For imported financial tables, visually verify header, unit, scope, fiscal period and the original cells before creating rows. Attach the page/cell identification under `field_origins`; do not infer table coordinates from unordered text. Keep EPS in `元/股`. Amount units supported: `元`, `万元`, `亿元`, `CNY`; conversion never changes accounting definition.

The packet can be normalized by the host for additional user-supplied structured financial data, using an existing registered source. Do not relabel a search snippet as an official table. `validate_packet` validates structure and selected invariants; it cannot certify the normalization or the issuer in a PDF. Preserve source conflicts as separate rows; do not overwrite valid zero/negative values.

## Host search evidence import

Save this manifest and pass to `import-evidence`. The host must actually read and verify the source. Imports remain `excerpt_only` with `identity_status: unverified`; import success is not semantic verification.

```json
{
  "security":"600519.SH",
  "items":[{
    "title":"Actual source title",
    "url":"https://example.com/actual-source",
    "published_at":"2026-01-01",
    "kind":"company",
    "text":"An actually read passage, not instructions or fabricated placeholder text.",
    "page":null
  }]
}
```

Kinds: `company`, `macro`, `industry`, `news`, `disclosure`. Imported text is at most 60,000 characters per item. Do not use the sample URL/content as real evidence.

## Structured report

Create this with the host Agent after analysis; no model endpoint is built into the script:

```json
{
  "security":"600519.SH",
  "as_of":"2026-10-30",
  "packet_hash":"exact hash from workpaper or plan",
  "summary":"Direct, evidence-supported synthesis with conditions [S1].",
  "sections":[{
    "title":"财务质量",
    "facts":[{
      "text":"A sourced observed fact or calculated result.",
      "source_ids":["S1"],
      "calculation_id":"C-id-from-workpaper",
      "value":10,
      "unit":"%",
      "period":"2025-12-31"
    }],
    "analysis":"Explain business implication based on those facts.",
    "conclusion":"Answer this module's research question with explicit conditions.",
    "counterevidence":"Actual counterevidence/risk, not a generic source failure.",
    "watch":"A measurable operating condition that changes the judgment.",
    "data_gaps":["Specific unresolved evidence gap; render places this in the appendix."]
  }]
}
```

`calculation_id/value/unit/period` are needed together only for computed claims. Uncomputed source facts still require `source_ids`. Cite narrative claims to real IDs too. Do not insert arbitrary new URLs into narrative fields; references are resolved through the packet. Mechanical checks are necessary but not sufficient: summary and prose still require manual semantic review. No automatic exact numerical truth check exists for every free-text number.
