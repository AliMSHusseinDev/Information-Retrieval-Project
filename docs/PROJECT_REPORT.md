# Information Storage and Retrieval — Technology Version

## Overview and scope

IR Project retrieves exact phrases from the assigned ten Technology documents and
ranks matching documents using normalized TF-IDF cosine similarity. The seven-page
university PDF defines Parts A, B, and C. The web GUI, charts, study guide, and
Windows packaging are additional application features, not replacements for the
academic outputs. Every displayed calculation comes from the computed model.

## Tools, dataset, and architecture

- Python 3.12, Apache Spark / PySpark 4.0.1, OpenJDK 21.
- Flask 3.1.2 and Waitress 3.0.2 serve the interactive application.
- Jinja, HTML5, CSS3, vanilla JavaScript, and local Chart.js 4.4.9 render the GUI.
- Original TXT documents remain in `data/`, without stemming or stop-word removal.
- Collection size: **10 documents, 27 terms, 64 tokens**. d5 retains the word `and`.

```text
TXT → Spark wholeTextFiles → flatMap positions → groupByKey → positional index
    → TF / weighted TF / DF / IDF → TF-IDF → L2 norms → normalized vectors
    → JSON + CSV outputs → Flask loads the model → phrase filters → cosine → GUI
```

Preprocessing is separate from interactive search. Spark is run once when the
collection changes, never per HTTP request. A SHA-256 source fingerprint and a
model schema version reject missing or outdated preprocessing results.

## Part A: positional indexing

Spark reads all source files with `wholeTextFiles`. Each worker lowercases and
splits text on whitespace, enumerates from 1, and emits a record for every token:

```text
((term, document_id), position)
```

`groupByKey` assembles all occurrences for each term/document pair. Positions are
sorted, terms are alphabetic, and document IDs use numeric order. The small final
index is collected on the driver. For example, `machine` in d5 has `[1, 3, 9]`,
while `learning` in d5 has `[2, 10]`. The full index is submitted as JSON and shown
in the searchable index explorer.

## Part B: mathematical conventions

For a term t and document d:

```text
TF(t,d) = number of positions
WeightedTF(t,d) = 1 + log10(TF(t,d)) if TF > 0; otherwise 0
DF(t) = number of distinct documents containing t
IDF(t) = log10(N / DF(t)), N = 10
TF-IDF(t,d) = WeightedTF(t,d) × IDF(t)
Length(d) = sqrt(Σ_t TF-IDF(t,d)²)
NormalizedTF-IDF(t,d) = TF-IDF(t,d) / Length(d)
```

For the query, count query tokens, apply the same weighted-TF formula, multiply
by the **existing collection IDF**, then L2-normalize. Unknown terms have no
collection dimension and an exact phrase containing an unknown term cannot match.
Zero-length vectors safely remain zero. No intermediate value is rounded.

Example: `TF(machine,d5)=3`, weighted TF ≈ 1.4771, DF = 5, IDF ≈ 0.3010,
TF-IDF ≈ 0.4447, document length ≈ 1.5526, normalized weight ≈ 0.2864.
For `machine learning`, both query weights normalize to 0.7071. The d5 score is
approximately `0.7071×0.2864 + 0.7071×0.2523 = 0.3809`.

### Document lengths

| Document | L2 norm | Document | L2 norm |
|---|---:|---|---:|
| d1 | 0.4257 | d6 | 1.3278 |
| d2 | 1.4850 | d7 | 1.5594 |
| d3 | 1.6691 | d8 | 2.0577 |
| d4 | 1.7707 | d9 | 1.5033 |
| d5 | 1.5526 | d10 | 1.8031 |

### Exact phrase results

| Phrase | Document → starting positions |
|---|---|
| machine learning | d1 → [1]; d2 → [1]; d5 → [1,9]; d7 → [4]; d10 → [1,5] |
| data science | d3 → [1]; d5 → [6]; d8 → [1] |

A two-token phrase starting at p spans positions p through p+1. Arbitrary phrases
use the same positional join: for offset i, keep starts where token i occurs at
start+i. Repeated and overlapping occurrences are preserved.

### Query rankings (actual calculated output, presented to four decimals)

| Query | Query L2 norm | Descending ranking and cosine similarity |
|---|---:|---|
| machine learning | 0.425721 | d1 1.0000; d5 0.3809; d10 0.3072; d2 0.2867; d7 0.2730 |
| data science | 0.545341 | d5 0.3513; d3 0.3267; d8 0.2715 |
| machine learning AND data science | 0.691834 | d5 0.5113 |
| machine learning AND NOT data science | 0.425721 | d1 1.0000; d10 0.3072; d2 0.2867; d7 0.2730 |

All production results are calculated. These reference-style numbers are
educational documentation; independent constants for validation live in tests.

## Five mandatory theoretical explanations

### 1. How do positions support phrase queries?

A term-only index proves that words exist but cannot prove their order or
adjacency. Position lists permit the algorithm to require consecutive locations.
For d5, machine positions `[1,3,9]` and learning positions `[2,10]` yield starts
`[1,9]` because only 1+1 and 9+1 occur in the learning list. Machine at 3 does not
start this phrase. The algorithm checks the index, not raw substring text.

### 2. How are DF and IDF related, and why does repetition affect TF?

DF counts distinct documents, regardless of repetition inside one document.
IDF is inversely related through `log10(N/DF)`: widespread terms get lower weights.
Data appears in 7 documents so its IDF is 0.1549; science appears in 3 so its IDF
is 0.5229. Machine occurs 3 times in d5, increasing its TF but contributing only
one document to DF. Weighted TF uses a logarithm so repetition helps without
letting one repetitive document dominate arbitrarily.

### 3. Why use TF-IDF and vector normalization?

TF-IDF combines local importance (weighted term frequency) and collection
specificity (IDF). Normalization divides each component by the vector's L2 norm,
removing overall magnitude from the comparison. A long document does not gain a
high score merely by having more tokens. We compare directions in the same
vocabulary space. Nonzero normalized vectors have squared components summing to 1.

### 4. How do similarity scores rank documents?

For L2-normalized vectors, cosine similarity equals their dot product:
`Σ_t normalized_query(t) × normalized_document(t,d)`. Sort the matching documents
by decreasing score, then numeric document ID for deterministic ties. Phrase
matching controls eligibility; cosine controls the order. d1 is exactly machine
learning, so it aligns with that query and scores 1. Other matched documents have
weight on extra terms and therefore score lower.

### 5. How do AND and AND NOT differ here?

Let A be the machine-learning phrase set `{d1,d2,d5,d7,d10}` and B the data-science
phrase set `{d3,d5,d8}`. AND returns `A ∩ B = {d5}`. Its query vector contains both
positive phrases. AND NOT returns `A − B = {d1,d2,d7,d10}` and ranks using only the
positive phrase. d2 and d10 contain data but not the complete phrase data science,
so they remain. The negative phrase never removes dimensions from a document vector.

## Part C: submitted evidence and reproducibility

`outputs/` contains the complete index, raw/weighted TF, DF/IDF, TF-IDF, document
lengths, normalized vectors, phrase/Boolean results, similarity scores, rankings,
and model provenance. CSV and JSON keep full precision. The export center checks
file existence and can bundle all outputs in a real ZIP. Actual browser captures
are in `screenshots/`, and execution evidence is in `docs/VALIDATION.md`.

The validation script independently checks the complete PDF index and normalized
table, every formula-derived matrix cell, all query scores/positions/rankings,
HTTP routes, export contents, invalid requests, and stale-data handling. The
optional browser smoke test exercises real controls, downloads, and small screens.

The Windows executable build remains a Windows-only step; neither its existence
nor Windows execution is claimed here. See the README for exact Docker,
PowerShell, Linux, and packaging commands.

## Conclusion

The system implements the assigned Spark positional index and all retrieval
calculations while keeping their code independent of the presentation layer.
The interface makes both the final ranking and its intermediate mathematics
inspectable, and the generated program outputs support the required submission.
