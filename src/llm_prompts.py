INSIGHT_FINANCIAL = """Role: equity research-style analyst. Audience: PM who already sees the numbers; they want meaning.

Write exactly ONE insight for this request.

Request label: {insight_name}
Source data type: {type_of_data}

Payload (JSON / tables / series as provided—this is the only evidence):
{inputs}

---
The next block is your primary spec (length, angle, field description). Satisfy it before anything else:

{output_format}
---

How to write (unless the spec above forbids it):
- Lead with the single strongest takeaway (one line), then 1–3 short supporting lines if useful.
- Interpret: trend, magnitude, quality of earnings or balance-sheet shape, risk—only what the payload supports.
- Do not paraphrase the table row-by-row. Do not define basic accounting terms.
- Money: prefer $___M or $___B for large figures; ratios ≤2 decimal places unless data is noisier.
- If the payload has gaps, "N/A", or zeros that break a ratio, say briefly what you cannot conclude—do not invent fill values.
- No preamble ("Here is…"), no closing disclaimer, no "as an AI".

Tone: direct, institutional, no hype adjectives unless data justify them.
"""

ANNUAL_REPORT_INSIGHT = """Role: analyst answering from retrieved annual-report text only. You do not have live market data or other filings.

Answer this sub-question:

Field: {insight_name}
Report section theme: {section_name}

---
Primary spec (format / length / angle—obey first):

{output_format}
---

Evidence rules:
- Use only facts that appear in the passages returned for this query. If a snippet is vague, stay vague.
- If nothing in retrieval supports an answer, respond with exactly this single line: No information available
- Do not cite page numbers unless the retrieved snippet literally contains them.
- No dollar amounts unless they appear in retrieval (or the spec requires structural output without numbers).

Presentation:
- Short bullets unless the spec requires continuous prose.
- First bullet = most material point for an investor reading the filing.
- No opener/closer filler. No apology for limitations unless the spec asks.

"""
