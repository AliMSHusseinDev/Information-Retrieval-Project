# Requirements map

The seven-page supplied PDF is the academic specification. The pasted brief adds
the Flask interface, exports, packaging, and study materials. Technology is the
assigned dataset; the other domains mentioned on PDF page 1 are not selected.

| Requirement | Implementation | Visible / submitted output | Verification |
|---|---|---|---|
| Exact ten documents; lowercase whitespace; 1-based positions | data/, src/indexing.py | Index explorer, source TXT files | validate.py checks every token and position |
| Part A: real Spark positional index | wholeTextFiles → flatMap → groupByKey | outputs/positional_index.json | Real Spark execution; independent complete index fixture |
| Raw and weighted TF, DF/IDF | src/calculations.py | Six analytics tabs; CSV files | All matrix cells and rounded PDF IDFs |
| TF-IDF, L2 lengths, normalization | src/calculations.py | Tables, heatmap, CSV | All cells; all ten PDF lengths; unit norms |
| Exact contiguous arbitrary phrases | src/queries.py | Search cards, starts and ranges | Both PDF phrases; repeated/unknown/reversed tokens |
| AND intersection, AND NOT difference of phrase sets | src/queries.py | Search modes and query exports | Required sets and rankings |
| Collection IDF, query L2 norm, cosine, rankings | src/calculations.py, src/queries.py | Mathematics page and result details | All four PDF rankings and scores |
| Part C source and program outputs | Source, outputs/, screenshots/ | Export center, generated files | API, file contents, real browser checks |
| Five theoretical explanations | docs/PROJECT_REPORT.md | Report | Dedicated numbered explanations |
| Additional six-page GUI / local Chart.js | templates/, static/ | Dashboard through export center | Browser interaction and responsive smoke checks |
| Additional Windows launcher / executable build | launcher.py, *.bat | Waitress server and browser | Launcher tested on Linux; Windows build requires Windows |
| Additional Arabic learning guide | docs/STUDY_GUIDE_AR.md | Egyptian Arabic guide | Function map and worked examples |

No search results or production matrices are reference constants. Reference
numbers appear only in tests and educational documentation. Readiness evidence
and platform limitations are recorded in docs/VALIDATION.md after execution.
