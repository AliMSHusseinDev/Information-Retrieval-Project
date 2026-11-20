import "./import.js";
import { barChart } from "./charts.js";

const $ = (id) => document.getElementById(id);
const format = (number, digits = 4) => Number(number).toFixed(digits);
let model;
let presets;

// All text from the collection/query is inserted as text, never interpreted as HTML.
function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = text;
  return node;
}
function replace(node, children) {
  node.replaceChildren(...children);
}
function link(text, href, className = "text-link") {
  const node = element("a", className, text);
  node.href = href;
  return node;
}
function button(text, className, handler) {
  const node = element("button", className, text);
  node.type = "button";
  node.addEventListener("click", handler);
  return node;
}
function table(headers, rows) {
  const node = element("table");
  const head = element("thead");
  const headRow = element("tr");
  headers.forEach((text) => {
    const cell = element("th", "", text);
    cell.scope = "col";
    headRow.append(cell);
  });
  head.append(headRow);
  node.append(head);
  const body = element("tbody");
  rows.forEach((row) => {
    const tr = element("tr");
    row.forEach((value, index) => {
      const cell = element("td", "", String(value));
      if (index && Number(value) === 0) cell.classList.add("zero");
      tr.append(cell);
    });
    body.append(tr);
  });
  node.append(body);
  return node;
}
async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => {
    $("toast").hidden = true;
  }, 2600);
}
async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied to clipboard.");
  } catch {
    toast("Clipboard is unavailable. Select and copy the visible values.");
  }
}
function highlight(text, ranges) {
  const fragment = document.createDocumentFragment();
  text.split(/\s+/).forEach((word, index) => {
    if (index) fragment.append(document.createTextNode(" "));
    const hit = ranges.some(
      ([start, end]) => index + 1 >= start && index + 1 <= end,
    );
    fragment.append(
      hit ? element("mark", "", word) : document.createTextNode(word),
    );
  });
  return fragment;
}
function saveSearch(value) {
  try {
    sessionStorage.setItem(`lumen-query:${document.baseURI}`, JSON.stringify(value));
  } catch {
    /* Storage can be disabled. */
  }
}
function restoredSearch() {
  try {
    return JSON.parse(sessionStorage.getItem(`lumen-query:${document.baseURI}`));
  } catch {
    return null;
  }
}

function dashboard() {
  const docs = Object.keys(model.documents);
  $("imported-names").append(table(["Document", "Original file", "Preview"], docs.map(doc => [doc, model.filenames[doc], model.documents[doc].slice(0, 80)])));
  const totalTokens = Object.values(model.documents).reduce(
    (sum, text) => sum + text.split(/\s+/).length,
    0,
  );
  const cards = [
    ["Total documents", docs.length, "Original TXT source files", "▤"],
    [
      "Unique terms",
      Object.keys(model.index).length,
      "Complete collection vocabulary",
      "≡",
    ],
    ["Total tokens", totalTokens, "Every occurrence, preserved", "▥"],
    ["Suggested queries", presets.length, "From the imported text", "⌕"],
  ];
  replace(
    $("kpi-grid"),
    cards.map(([label, value, foot, icon]) => {
      const card = element("article", "kpi");
      card.append(
        element("div", "kpi-label", label),
        element("div", "kpi-number", value),
        element("div", "kpi-foot", foot),
        element("div", "kpi-icon", icon),
      );
      return card;
    }),
  );
  barChart(
    "document-chart",
    docs,
    docs.map((doc) => model.documents[doc].split(/\s+/).length),
    { label: "Tokens", color: "#6b9fd7" },
  );
  const frequencies = Object.keys(model.index)
    .map((term) => [
      term,
      Object.values(model.raw_tf[term]).reduce((a, b) => a + b, 0),
    ])
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 6);
  barChart(
    "terms-chart",
    frequencies.map((row) => row[0]),
    frequencies.map((row) => row[1]),
    { label: "Occurrences", horizontal: true },
  );
  const dfCounts = {};
  Object.values(model.df).forEach((df) => {
    dfCounts[df] = (dfCounts[df] || 0) + 1;
  });
  barChart(
    "df-chart",
    Object.keys(dfCounts).map(
      (value) => `${value} doc${value === "1" ? "" : "s"}`,
    ),
    Object.values(dfCounts),
    { label: "Terms", color: "#9e91dd" },
  );
  const steps = [
    ["Dataset", "Original text files"],
    ["Spark", "Distributed indexing"],
    ["Index", "Terms & positions"],
    ["TF-IDF", "Weighted vectors"],
    ["Query", "Exact phrase matches"],
    ["Ranking", "Cosine similarity"],
  ];
  replace(
    $("pipeline"),
    steps.map(([name, detail], i) => {
      const step = element("div", "pipeline-step");
      step.append(
        element("span", "pipeline-number", `0${i + 1}`),
        element("strong", "", name),
        element("p", "", detail),
      );
      return step;
    }),
  );
  replace(
    $("dashboard-presets"),
    presets.map((preset, i) => {
      const node = link(preset.label, `search?preset=${i}`, "query-link");
      node.append(element("span", "", "→"));
      return node;
    }),
  );
  document.querySelectorAll(".vector-card").forEach((node, i) => {
    const term = frequencies[i]?.[0] ?? frequencies[0][0];
    node.querySelector("span").textContent = term;
    const weight = model.normalized[term][docs[0]];
    node.querySelector("b").textContent = format(weight);
    node.querySelector(".mini-track i").style.width = `${weight * 100}%`;
  });
}

function documentLabel(doc) {
  const name = model.filenames[doc];
  return name === doc + ".txt" ? name : doc + " · " + name;
}

function indexExplorer() {
  const terms = Object.keys(model.index);
  let selected = terms.includes("machine") ? "machine" : terms[0];
  let selectedDoc = Object.keys(model.index[selected])[0];
  $("term-count").textContent = terms.length;
  function renderVocabulary() {
    const visible = terms.filter((term) =>
      term.includes($("vocabulary-search").value.toLowerCase()),
    );
    replace(
      $("vocabulary-list"),
      visible.map((term) => {
        const node = button(
          term,
          `term-button ${term === selected ? "selected" : ""}`,
          () => {
            selected = term;
            selectedDoc = Object.keys(model.index[term])[0];
            render();
          },
        );
        node.setAttribute("aria-pressed", String(term === selected));
        node.append(element("span", "", model.df[term]));
        return node;
      }),
    );
    if (!visible.length)
      $("vocabulary-list").append(
        element("p", "no-rows", "No matching terms."),
      );
  }
  function render() {
    renderVocabulary();
    $("selected-term").textContent = selected;
    const postings = model.index[selected];
    $("posting-summary").textContent =
      `${Object.keys(postings).length} documents · ${Object.values(postings).reduce((sum, positions) => sum + positions.length, 0)} occurrences`;
    replace(
      $("postings"),
      Object.entries(postings).map(([doc, positions]) => {
        const node = button(
          "",
          `posting ${doc === selectedDoc ? "selected" : ""}`,
          () => {
            selectedDoc = doc;
            render();
          },
        );
        node.setAttribute(
          "aria-label",
          `${doc}, positions ${positions.join(", ")}`,
        );
        node.append(
          element("b", "", doc),
          element("span", "", `[${positions.join(", ")}]`),
          element(
            "small",
            "",
            `${positions.length} occurrence${positions.length === 1 ? "" : "s"}`,
          ),
        );
        return node;
      }),
    );
    $("preview-document").textContent = documentLabel(selectedDoc);
    const positions = postings[selectedDoc];
    $("document-preview").replaceChildren(
      highlight(
        model.documents[selectedDoc],
        positions.map((p) => [p, p]),
      ),
    );
    replace(
      $("token-strip"),
      model.documents[selectedDoc].split(/\s+/).map((word, i) => {
        const node = element(
          "span",
          `token ${positions.includes(i + 1) ? "hit" : ""}`,
          word,
        );
        node.append(element("small", "", i + 1));
        return node;
      }),
    );
  }
  $("vocabulary-search").addEventListener("input", renderVocabulary);
  $("copy-positions").addEventListener("click", () =>
    copy(JSON.stringify({ [selected]: model.index[selected] }, null, 2)),
  );
  $("full-index").append(
    table(
      ["Term", "Documents and 1-based positions"],
      terms.map((term) => [
        term,
        Object.entries(model.index[term])
          .map(([doc, positions]) => `${doc}: [${positions.join(", ")}]`)
          .join(" · "),
      ]),
    ),
  );
  render();
}

const matrixTypes = {
  raw_tf: [
    "Raw TF",
    "Raw term frequency",
    "TF(t,d) = number of occurrences of t in d. Count all positions, including repeated words.",
  ],
  weighted_tf: [
    "Weighted TF",
    "Logarithmic term frequency",
    "WeightedTF = 1 + log10(TF), when TF > 0; otherwise 0. Repetition increases weight with diminishing returns.",
  ],
  df_idf: [
    "DF / IDF",
    "Document & inverse document frequency",
    "DF counts distinct documents. IDF = log10(N / DF). Common terms receive less weight.",
  ],
  tfidf: [
    "TF-IDF",
    "Term frequency × inverse document frequency",
    "TF-IDF = WeightedTF × collection IDF. A term is important when it is frequent in a document and rare across the collection.",
  ],
  lengths: [
    "Vector lengths",
    "Document vector lengths",
    "Length(d) = sqrt(Σ TF-IDF(t,d)²). This is the L2 norm before normalization.",
  ],
  normalized: [
    "Normalized TF-IDF",
    "Normalized document vectors",
    "NormalizedTF-IDF = TF-IDF / document length. Nonzero document vectors have unit length, making cosine comparisons comparable.",
  ],
};
function analytics() {
  let type = "raw_tf";
  let heatmap = false;
  const docs = Object.keys(model.documents);
  docs.forEach((doc) => {
    const option = element("option", "", doc);
    option.value = doc;
    $("document-filter").append(option);
  });
  function render() {
    const titles = matrixTypes[type];
    $("matrix-title").textContent = titles[1];
    $("matrix-explanation").textContent = titles[2];
    $("matrix-subtitle").textContent =
      type === "df_idf"
        ? "Collection statistics · base-10 logarithms"
        : type === "lengths"
          ? "L2 magnitude before normalization"
          : "Terms × documents · computed from the Spark index";
    $("matrix-export").href =
      `download/${type === "lengths" ? "document_lengths" : type}.csv`;
    const filter = $("matrix-search").value.trim().toLowerCase();
    const shownDocs = $("document-filter").value
      ? [$("document-filter").value]
      : docs;
    const terms = Object.keys(model.index).filter((term) =>
      term.includes(filter),
    );
    const precision = $("precision").value;
    function numeric(value) {
      return precision === "full"
        ? String(value)
        : format(value, Number(precision));
    }
    let headers, rows;
    if (type === "df_idf") {
      headers = ["Term", "DF", "IDF"];
      rows = terms.map((term) => [
        term,
        model.df[term],
        numeric(model.idf[term]),
      ]);
    } else if (type === "lengths") {
      headers = ["Document", "L2 vector length"];
      rows = shownDocs.map((doc) => [doc, numeric(model.lengths[doc])]);
    } else {
      headers = ["Term", ...shownDocs];
      rows = terms.map((term) => [
        term,
        ...shownDocs.map((doc) => numeric(model[type][term][doc])),
      ]);
    }
    const node = table(headers, rows);
    if ($("density").value === "compact") node.classList.add("compact");
    if (heatmap) {
      // The numeric labels stay visible: color never carries the information alone.
      const values = rows.flatMap((row) => row.slice(1).map(Number));
      const max = Math.max(...values, 0);
      node.querySelectorAll("tbody tr").forEach((row, i) => {
        Array.from(row.children)
          .slice(1)
          .forEach((cell, j) => {
            const value = Number(rows[i][j + 1]);
            cell.style.backgroundColor = `rgba(72, 213, 181, ${max ? 0.05 + (0.42 * value) / max : 0.05})`;
            cell.style.color = "#e4f7f1";
            cell.title = `${rows[i][0]} / ${headers[j + 1]}: ${type in model && model[type][rows[i][0]] ? model[type][rows[i][0]][shownDocs[j]] : rows[i][j + 1]}`;
          });
      });
    }
    replace(
      $("matrix-container"),
      rows.length
        ? [node]
        : [
            element(
              "p",
              "no-rows",
              "No terms match this filter. Reset to see the complete table.",
            ),
          ],
    );
    $("matrix-dimensions").textContent =
      `${rows.length} rows × ${headers.length - 1} ${type === "lengths" ? "value" : "columns"}`;
    $("matrix-search").disabled = type === "lengths";
    $("document-filter").disabled = type === "df_idf";
    $("heatmap-key").textContent = heatmap
      ? "Low ░ → High ▓ · Hover for exact values"
      : "Values are computed at full precision.";
    document.querySelectorAll("#matrix-tabs button").forEach((node) => {
      const selected = node.dataset.type === type;
      node.classList.toggle("selected", selected);
      node.setAttribute("aria-pressed", selected);
    });
  }
  Object.entries(matrixTypes).forEach(([key, titles]) => {
    const node = button(titles[0], "", () => {
      type = key;
      render();
    });
    node.dataset.type = key;
    $("matrix-tabs").append(node);
  });
  ["matrix-search", "document-filter", "precision", "density"].forEach((id) =>
    $(id).addEventListener(id === "matrix-search" ? "input" : "change", render),
  );
  $("clear-filters").addEventListener("click", () => {
    $("matrix-search").value = "";
    $("document-filter").value = "";
    $("precision").value = "4";
    $("density").value = "comfortable";
    render();
  });
  ["table", "heatmap"].forEach((view) =>
    $(view + "-mode").addEventListener("click", () => {
      heatmap = view === "heatmap";
      ["table", "heatmap"].forEach((name) => {
        $(name + "-mode").classList.toggle("selected", name === view);
        $(name + "-mode").setAttribute("aria-pressed", name === view);
      });
      render();
    }),
  );
  render();
}

function contributionTable(result) {
  return table(
    ["Term", "Query weight", "Document weight", "Product"],
    result.contributions.map((row) => [
      row.term,
      format(row.query_weight),
      format(row.document_weight),
      format(row.product, 8),
    ]),
  );
}
function resultCard(result, query) {
  const card = element("article", "result-card");
  const header = element("div", "result-header");
  const identity = element("div", "result-identity");
  identity.append(
    element("span", "rank-badge", String(result.rank).padStart(2, "0")),
    element("strong", "", documentLabel(result.document)),
  );
  if (result.rank === 1) identity.append(element("small", "", "TOP MATCH"));
  const score = element("div", "score", format(result.similarity));
  score.append(element("small", "", "COSINE SIMILARITY"));
  header.append(identity, score);
  const text = element("p", "result-text");
  text.append(
    highlight(result.text, [
      ...result.first.ranges,
      ...(query.mode === "and" && result.second ? result.second.ranges : []),
    ]),
  );
  const positions = element("div", "position-chips");
  positions.append(
    element(
      "span",
      "position-chip",
      `Starts: ${result.first.starts.join(", ")}`,
    ),
    element(
      "span",
      "position-chip",
      `Ranges: ${result.first.ranges.map((range) => range.join("–")).join(", ")}`,
    ),
  );
  if (result.second)
    positions.append(
      element(
        "span",
        "position-chip",
        `Second phrase: ${result.second.ranges.map((range) => range.join("–")).join(", ")}`,
      ),
    );
  const details = element("details");
  details.append(element("summary", "", "Inspect term weights & dot product"));
  const scroll = element("div", "table-scroll");
  scroll.append(contributionTable(result));
  details.append(
    scroll,
    element(
      "p",
      "formula",
      `Σ products = ${result.similarity.toPrecision(12)}`,
    ),
  );
  card.append(header, text, positions, details);
  return card;
}
function renderResults(data) {
  $("result-heading").textContent =
    `${data.count} matching document${data.count === 1 ? "" : "s"}`;
  $("result-subtitle").textContent =
    data.mode === "and_not"
      ? "Second phrase filters documents; only positive terms contribute to ranking."
      : "Exact phrase matches, ranked by normalized TF-IDF cosine similarity.";
  replace(
    $("search-results"),
    data.results.map((result) => resultCard(result, data)),
  );
  if (!data.count) {
    const empty = element("div", "empty-state panel");
    empty.append(
      element("div", "empty-icon", "⌕"),
      element("h3", "", "No exact phrase matches"),
      element(
        "p",
        "",
        data.unknown_terms.length
          ? `Outside the vocabulary: ${data.unknown_terms.join(", ")}. Try the vocabulary explorer.`
          : "These terms do not occur consecutively in the required order, or the Boolean filter removes the matches.",
      ),
    );
    empty.append(link("Explore the vocabulary →", "index"));
    $("search-results").append(empty);
  }
  barChart(
    "ranking-chart",
    data.results.map((row) => row.document),
    data.results.map((row) => row.similarity),
    { horizontal: true, label: "Cosine similarity", max: 1 },
  );
}
function mathStep(number, title, note) {
  const step = element("section", "panel math-step");
  const heading = element("div", "step-heading");
  heading.append(
    element("span", "step-number", String(number).padStart(2, "0")),
    element("h3", "", title),
  );
  step.append(heading, element("p", "", note));
  return step;
}
function queryTable(data, columns) {
  const labels = {
    term: "Term",
    tf: "Raw TF",
    weighted_tf: "Weighted TF",
    idf: "Collection IDF",
    tfidf: "Query TF-IDF",
    normalized: "Normalized query",
  };
  const scroll = element("div", "table-scroll");
  scroll.append(
    table(
      columns.map((key) => labels[key]),
      data.query.rows.map((row) =>
        columns.map((key) =>
          key === "term" || key === "tf" ? row[key] : format(row[key]),
        ),
      ),
    ),
  );
  return scroll;
}
function renderMathematics(data) {
  const container = element("div", "math-steps");
  const first = mathStep(
    1,
    "Tokenization",
    data.mode === "and_not"
      ? "Lowercase and split the positive phrase on whitespace. The excluded phrase is a filter only."
      : "Lowercase and split positive phrases on whitespace. No stop-word removal or stemming.",
  );
  const tokens = element("div", "token-chips");
  data.query.tokens.forEach((token) =>
    tokens.append(element("span", "token-chip", token)),
  );
  first.append(tokens);
  container.append(first);
  const steps = [
    [
      2,
      "Query term frequency",
      "Count repeated terms in the query itself.",
      ["term", "tf"],
    ],
    [
      3,
      "Weighted query TF",
      "Use 1 + log10(TF), preserving full precision.",
      ["term", "tf", "weighted_tf"],
    ],
    [
      4,
      "Collection IDF",
      "Use log10(N / DF) from the document collection. Never calculate a new IDF from the query.",
      ["term", "idf"],
    ],
    [
      5,
      "Query TF-IDF",
      "Multiply weighted query TF by collection IDF.",
      ["term", "weighted_tf", "idf", "tfidf"],
    ],
  ];
  steps.forEach(([number, title, note, columns]) => {
    const step = mathStep(number, title, note);
    step.append(queryTable(data, columns));
    container.append(step);
  });
  const norm = mathStep(
    6,
    "Query vector length",
    "Take the square root of the sum of squared query TF-IDF weights.",
  );
  norm.append(
    element(
      "div",
      "formula",
      `sqrt(${data.query.rows.map((row) => `${format(row.tfidf, 6)}²`).join(" + ") || "0"})`,
    ),
    element("div", "large-value", format(data.query.length, 6)),
  );
  container.append(norm);
  const normalize = mathStep(
    7,
    "Normalize the query",
    "Divide each query TF-IDF weight by the L2 length. A zero-length vector safely stays zero.",
  );
  normalize.append(queryTable(data, ["term", "tfidf", "normalized"]));
  container.append(normalize);
  const compare = mathStep(
    8,
    "Compare matching document dimensions",
    "The original normalized document vector stays unchanged. Compare weights for the same terms.",
  );
  const controls = element("div", "math-doc-controls");
  const field = element("div", "field");
  const label = element("label", "", "Matching document");
  label.htmlFor = "math-document";
  const select = element("select");
  select.id = "math-document";
  data.results.forEach((result) => {
    const option = element(
      "option",
      "",
      `${result.document} · rank ${result.rank}`,
    );
    option.value = result.document;
    select.append(option);
  });
  field.append(label, select);
  controls.append(
    field,
    button("Copy calculation", "button", () =>
      copy(
        JSON.stringify(
          {
            query: data.query,
            document: data.results.find((row) => row.document === select.value),
          },
          null,
          2,
        ),
      ),
    ),
  );
  const comparisons = element("div", "table-scroll");
  compare.append(controls, comparisons);
  container.append(compare);
  const dot = mathStep(
    9,
    "Dot product = cosine similarity",
    "Add the term-by-term products of the two normalized vectors.",
  );
  const dotFormula = element("div", "formula");
  const dotScore = element("div", "large-value");
  dot.append(dotFormula, dotScore);
  container.append(dot);
  function showDocument() {
    const result = data.results.find((row) => row.document === select.value);
    if (!result) {
      select.disabled = true;
      comparisons.textContent = "No matching document to compare.";
      dotFormula.textContent = "No matching document.";
      dotScore.textContent = "—";
      return;
    }
    comparisons.replaceChildren(contributionTable(result));
    dotFormula.textContent = result.contributions
      .map(
        (row) => `${format(row.query_weight)} × ${format(row.document_weight)}`,
      )
      .join(" + ");
    dotScore.textContent = format(result.similarity, 8);
  }
  select.addEventListener("change", showDocument);
  showDocument();
  const ranking = mathStep(
    10,
    "Rank by descending similarity",
    "Higher cosine similarity comes first. Ties use numeric document order.",
  );
  ranking.append(
    table(
      ["Rank", "Document", "Cosine similarity"],
      data.results.map((row) => [
        row.rank,
        row.document,
        format(row.similarity),
      ]),
    ),
  );
  if (!data.count)
    ranking.append(
      element("p", "", "No documents satisfy the phrase / Boolean filter."),
    );
  const note = element("details", "formula-note");
  note.append(
    element("summary", "", "Why can a longer document score lower?"),
    element(
      "p",
      "",
      "Normalization spreads weight across every term in a document. A short document entirely about the query can align more closely with the query direction. Negative phrases only affect the candidate set.",
    ),
  );
  ranking.append(note);
  container.append(ranking);
  $("math-content").replaceChildren(container);
}

function queryPage(isMath) {
  let mode = "phrase";
  let busy = false;
  function setMode(value) {
    mode = ["phrase", "and", "and_not"].includes(value) ? value : "phrase";
    document.querySelectorAll("[data-mode]").forEach((node) => {
      const active = node.dataset.mode === mode;
      node.classList.toggle("selected", active);
      node.setAttribute("aria-pressed", active);
    });
    $("other-field").hidden = mode === "phrase";
    $("other-input").required = mode !== "phrase";
    $("other-label").textContent =
      mode === "and_not"
        ? "Exclude this exact phrase"
        : "Also require this exact phrase";
  }
  function populate(preset) {
    setMode(preset.mode);
    $("phrase-input").value = preset.phrase;
    $("other-input").value = preset.other || "";
  }
  async function submit(event) {
    event?.preventDefault();
    if (busy) return;
    const payload = {
      mode,
      phrase: $("phrase-input").value,
      other: $("other-input").value,
    };
    if (
      !payload.phrase.trim() ||
      (mode !== "phrase" && !payload.other.trim())
    ) {
      $("query-message").textContent = "Enter all required phrases.";
      $("query-message").classList.add("invalid");
      return;
    }
    busy = true;
    $("search-button").disabled = true;
    $("search-button").textContent = "Searching…";
    $("query-message").classList.remove("invalid");
    $("query-message").textContent = "Calculating matches and similarity…";
    try {
      const data = await request("api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      saveSearch(payload);
      $("query-message").textContent = data.unknown_terms.length
        ? `Not in the collection: ${data.unknown_terms.join(", ")}.`
        : `${data.count} matching document${data.count === 1 ? "" : "s"} · Query length ${format(data.query.length, 6)} · Full precision retained`;
      if (isMath) renderMathematics(data);
      else renderResults(data);
    } catch (error) {
      $("query-message").textContent = error.message;
      $("query-message").classList.add("invalid");
    } finally {
      busy = false;
      $("search-button").disabled = false;
      $("search-button").textContent = "Search collection →";
    }
  }
  document
    .querySelectorAll("[data-mode]")
    .forEach((node) =>
      node.addEventListener("click", () => setMode(node.dataset.mode)),
    );
  $("query-form").addEventListener("submit", submit);
  presets.forEach((preset) =>
    $("query-presets").append(
      button(preset.label, "chip", () => {
        if (!busy) {
          populate(preset);
          submit();
        }
      }),
    ),
  );
  $("clear-search").addEventListener("click", () => {
    if (busy) return;
    $("query-form").reset();
    setMode("phrase");
    saveSearch(null);
    $("query-message").textContent =
      "Enter a phrase or choose one of the suggested queries.";
    $("query-message").classList.remove("invalid");
    if (isMath)
      $("math-content").replaceChildren(
        element(
          "div",
          "empty-state panel",
          "Run a query to explore its mathematics.",
        ),
      );
    else {
      $("search-results").replaceChildren(
        element(
          "div",
          "empty-state panel",
          "Enter a phrase to explore matching documents.",
        ),
      );
      $("result-heading").textContent = "Your next discovery starts here";
      $("result-subtitle").textContent =
        "Results are ranked by normalized TF-IDF cosine similarity.";
      barChart("ranking-chart", [], [], {
        horizontal: true,
        label: "Cosine similarity",
        max: 1,
      });
    }
    $("phrase-input").focus();
  });
  const param = new URLSearchParams(location.search).get("preset");
  const initial =
    param !== null && presets[Number(param)]
      ? presets[Number(param)]
      : restoredSearch();
  if (initial) {
    populate(initial);
    submit();
  } else if (isMath && presets.length) {
    populate(presets[0]);
    submit();
  } else
    barChart("ranking-chart", [], [], {
      horizontal: true,
      label: "Cosine similarity",
      max: 1,
    });
}

async function reports() {
  const descriptions = {
    "positional_index.json": [
      "Positional index",
      "Every term, document, and 1-based position.",
    ],
    "raw_tf.csv": ["Raw TF matrix", "Term occurrence counts across the imported files."],
    "weighted_tf.csv": [
      "Weighted TF matrix",
      "Logarithmic term weights: 1 + log10(TF).",
    ],
    "df_idf.csv": ["DF & IDF", "Collection-wide term frequency statistics."],
    "tfidf.csv": ["TF-IDF matrix", "Weighted TF multiplied by collection IDF."],
    "document_lengths.csv": [
      "Document vector lengths",
      "The L2 norm of each document vector.",
    ],
    "normalized.csv": [
      "Normalized TF-IDF",
      "Unit document vectors used for cosine similarity.",
    ],
    "phrase_queries.json": [
      "Phrase query results",
      "Positions, vectors, scores, and phrase rankings.",
    ],
    "boolean_queries.json": [
      "Boolean query results",
      "AND / AND NOT matches and their calculations.",
    ],
    "similarities.csv": [
      "Similarity scores",
      "Calculated cosine scores for all suggested queries.",
    ],
    "rankings.csv": [
      "Document rankings",
      "Ordered matches for the suggested queries.",
    ],
    "model.json": [
      "Complete processing model",
      "The full-precision Spark-generated collection.",
    ],
  };
  const files = await request("api/exports");
  $("exports-count").textContent =
    `${files.filter((file) => file.ready).length} / ${files.length} FILES READY`;
  replace(
    $("export-grid"),
    files.map((file) => {
      const [title, description] = descriptions[file.name];
      const card = element("article", "export-card");
      const head = element("div", "export-file");
      head.append(
        element("span", "file-type", file.name.split(".").pop().toUpperCase()),
        element(
          "span",
          file.ready ? "ready" : "",
          file.ready ? "● Generated" : "Missing",
        ),
      );
      card.append(
        head,
        element("h3", "", title),
        element("p", "", description),
        element(
          "div",
          "export-file",
          `${file.name} · ${(file.bytes / 1024).toFixed(1)} KB`,
        ),
      );
      if (file.ready)
        card.append(link("Download file ↓", "download/" + file.name));
      return card;
    }),
  );
}

$("collapse-sidebar").addEventListener("click", () => {
  const collapsed = document.body.classList.toggle("sidebar-collapsed");
  $("collapse-sidebar").setAttribute("aria-expanded", String(!collapsed));
  $("collapse-sidebar").setAttribute(
    "aria-label",
    collapsed ? "Expand sidebar" : "Collapse sidebar",
  );
});
$("help-button").addEventListener("click", () => $("help-dialog").showModal());
$("close-help").addEventListener("click", () => $("help-dialog").close());
if (document.body.dataset.loaded === "1") try {
  const data = await request("api/model");
  model = data.model;
  presets = data.presets;
  $("header-status").textContent = "Collection ready";
  const page = document.body.dataset.page;
  if (page === "dashboard") dashboard();
  if (page === "index") indexExplorer();
  if (page === "analytics") analytics();
  if (page === "search" || page === "mathematics")
    queryPage(page === "mathematics");
  if (page === "reports") await reports();
} catch (error) {
  $("app-error").hidden = false;
  $("app-error").textContent = error.message;
  $("header-status").textContent = "Needs attention";
}
