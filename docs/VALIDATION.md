# Validation record

Validated on **14 November 2026**, using the actual application and original
Technology dataset. The supplied PDF's reference constants are confined to test
fixtures and educational documentation; production scores are calculated.

## Native Spark and numerical/API validation — passed

```bash
/workspace/.venvs/ir/bin/python run_spark.py
/workspace/.venvs/ir/bin/python validate.py
```

The actual Spark 4.0.1 job used `wholeTextFiles`, `flatMap`, and `groupByKey`,
completed its worker stages, and generated **10 documents / 27 terms / 64 tokens**.
OpenJDK 21.0.13 and Python 3.12.14 were used. Spark's optional native-Hadoop-library
warning fell back to built-in Java classes; no Hadoop cluster is needed.

**11 tests executed, 11 passed, none skipped or disabled.** These groups verify:

1. Exact source documents and processing provenance.
2. Every posting and position from PDF page 3, with natural document sorting.
3. Every raw/weighted TF, DF/IDF, and TF-IDF cell using independent calculations;
   all ten reference document lengths and normalized unit-vector invariants.
4. All **270 normalized matrix cells** against PDF page 5 (including zeros).
5. Both assigned phrase queries, every starting position, and every token range.
6. All four query vector lengths, cosine scores, Boolean results, and rankings.
7. Reversed/repeated words, literal `and`, case/whitespace, unknown terms, negative
   phrase filtering, query repetitions, and zero-length vectors.
8. All six HTML routes and actual model/index/search API results.
9. Invalid input types/lengths/modes and unauthorized download paths.
10. CSV/JSON files and downloaded ZIP contents match calculated data.
11. Missing/stale outputs fail clearly, including when data changes after startup or saved results are rebuilt while an older model is in memory.

Reference numbers printed to four decimals are compared with absolute tolerance
0.00005; six-decimal query lengths use 0.0000005. Formula identities use tighter
precision. Raw exports retain unrounded numeric values.

| Query | Verified ranking (score) |
|---|---|
| machine learning | d1 (1.0000), d5 (0.3809), d10 (0.3072), d2 (0.2867), d7 (0.2730) |
| data science | d5 (0.3513), d3 (0.3267), d8 (0.2715) |
| AND | d5 (0.5113) |
| AND NOT | d1 (1.0000), d10 (0.3072), d2 (0.2867), d7 (0.2730) |

## Real browser integration — passed

System Chromium, driven by Playwright 1.62.0:

```bash
IR_BROWSER_EXECUTABLE=/usr/bin/chromium python tests/browser_smoke.py
```

The smoke test uses the running Waitress application and checks:

- Dashboard KPIs and chart document labels in numeric order.
- Help dialog and sidebar collapse.
- Vocabulary filter, d5's three machine occurrences, and original-token highlighting.
- Six analytics tabs, term/document filters, full precision, density, reset, heatmap
  values and exact hover titles.
- All four assigned search presets and visible result order, expanded contributions,
  keyboard Enter search, unknown-term state, and clear/reset.
- All ten mathematics stages and changing the selected comparison document.
- All 12 real export files and a downloaded ZIP with actual bytes.
- No external asset requests on dashboard load; Chart.js is local.
- All six routes at a **390px** viewport, without page-wide horizontal overflow.
- No browser JavaScript exceptions.

Actual screenshots (not mockups): `overview.png`, `positional-index.png`,
`analytics.png`, `search-phrase.png`, `search-and-not.png`,
`query-mathematics.png`, `exports.png`, and `mobile-search.png`, in `screenshots/`.
The mathematics page is long by design because the screenshot captures every stage.

## Desktop launcher — passed on Linux

```bash
/workspace/.venvs/ir/bin/python tests/launcher_smoke.py
```

The actual Waitress launcher was started as a subprocess. The check occupies its
preferred port, verifies functional readiness on an automatically selected port,
launches a duplicate that reuses the running instance, sends Enter to stop it,
and starts it again to verify lock cleanup. Browser opening is intentionally
disabled by the test. Windows OS locking/browser behavior is not verified here.

## Docker preprocessing — passed on Linux

```bash
docker build --secret id=pip_ca,src=/etc/ssl/certs/ca-certificates.crt -t lumen-ir-spark .
docker run --rm lumen-ir-spark sh -c 'python run_spark.py && python validate.py'
```

The first ordinary build encountered the cloud network's private CA during PyPI
TLS verification. Supplying the host's approved CA bundle through Docker's
optional build secret resolved it. Certificate checking stayed enabled; no
`--trusted-host`, insecure TLS flag, or checksum bypass was used. The CA bundle
is not copied into source or application assets. Ordinary public-network builds
need no CA option. The image independently ran Spark and all 11 validation groups.
Docker Desktop/PowerShell execution on Windows remains unverified.

## Packaging and remaining limits

- `Launch_IR.bat`, `build_exe.bat`, and an offline-ready one-folder PyInstaller
  resource configuration are provided.
- **No Windows executable has been built or tested in this Linux environment.**
  Build on Windows with `build_exe.bat`; distribute its entire output directory.
- `launcher.py` is tested on Linux. The GUI-only dependency installation is checked
  separately without PySpark or Java being imported by the interactive application.
- `pip check` reports no broken dependencies in the prepared full environment.
- Cloud configuration persistence, publication, and fresh-task restoration are
  separate platform operations; these tests validate the current application.
