// Capture the rendered result panels so filters, open details and precision match the screen.
const sections = {
  dashboard: "#main > section, #main > .section-heading, #main > details",
  analytics: ".analytics-panel",
  index: ".index-layout > div, #main > details[open]",
  mathematics: "#math-content",
  search: "#main > .section-heading, .search-layout",
};

function chartVector(canvas) {
  const chart = Chart.getChart(canvas);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${chart.width} ${chart.height}`);
  function draw(tag, attributes, text) {
    const node = document.createElementNS(svg.namespaceURI, tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
    if (text !== undefined) node.textContent = text;
    svg.append(node);
    return node;
  }
  const area = chart.chartArea;
  const horizontal = chart.options.indexAxis === "y";
  const valueAxis = horizontal ? chart.scales.x : chart.scales.y;
  for (const [i] of valueAxis.ticks.entries()) {
    const at = valueAxis.getPixelForTick(i);
    const points = horizontal
      ? { x1: at, x2: at, y1: area.top, y2: area.bottom }
      : { x1: area.left, x2: area.right, y1: at, y2: at };
    draw("line", { ...points, stroke: "#233247" });
  }
  const series = chart.data.datasets[0];
  for (const [i, bar] of chart.getDatasetMeta(0).data.entries()) {
    const { x, y, base, width, height } = bar.getProps(["x", "y", "base", "width", "height"], true);
    const rect = horizontal
      ? { x: Math.min(base, x), y: y - height / 2, width: Math.abs(x - base), height }
      : { x: x - width / 2, y: Math.min(base, y), width, height: Math.abs(y - base) };
    const node = draw("rect", { ...rect, rx: 3, fill: series.backgroundColor });
    const title = document.createElementNS(svg.namespaceURI, "title");
    title.textContent = chart.data.labels[i] + " · " + series.data[i];
    node.append(title);
  }
  for (const scale of Object.values(chart.scales)) {
    for (const tick of scale.getLabelItems()) {
      const [x, y] = tick.options.translation;
      const angle = tick.options.rotation * 180 / Math.PI;
      const anchor = { center: "middle", right: "end", left: "start" }[tick.options.textAlign] || "middle";
      draw("text", { x: 0, y: tick.textOffset, transform: `translate(${x} ${y}) rotate(${angle})`,
        "text-anchor": anchor, "dominant-baseline": "central", "font-size": tick.font.size, fill: "#94a9c1" }, tick.label);
    }
  }
  if (horizontal) draw("text", { x: (area.left + area.right) / 2, y: chart.height - 3,
    "font-size": 9, "text-anchor": "middle", fill: "#94a9c1" }, series.label);
  return svg;
}

function caption(page) {
  if (page === "analytics") {
    const read = (id) => document.getElementById(id);
    return [
      read("matrix-tabs").querySelector(".selected").textContent,
      read("heatmap-mode").classList.contains("selected") ? "Heatmap" : "Table",
      !read("matrix-search").disabled && read("matrix-search").value,
      !read("document-filter").disabled && read("document-filter").selectedOptions[0].text,
      read("precision").selectedOptions[0].text,
    ].filter(Boolean).join(" · ");
  }
  if (page === "index") return document.getElementById("selected-term").textContent
    + " · " + document.getElementById("preview-document").textContent;
  return document.getElementById("main").dataset.resultQuery || "";
}

function collectPanels(page, root) {
  for (const panel of document.querySelectorAll(sections[page])) {
    const clone = panel.cloneNode(true);
    const charts = panel.querySelectorAll("canvas");
    clone.querySelectorAll("canvas").forEach((canvas, index) => canvas.replaceWith(chartVector(charts[index])));
    clone.querySelectorAll(".toolbar, .view-toolbar, button:not(.posting), .full-width, [hidden]").forEach(node => node.remove());
    if (page !== "dashboard") clone.querySelectorAll(".text-link").forEach(node => node.remove());
    clone.querySelectorAll("select").forEach(select => {
      const selected = panel.querySelector("select")?.selectedOptions[0]?.text || "No matching document";
      select.replaceWith(document.createTextNode(selected));
    });
    const details = [clone, ...clone.querySelectorAll("details")].filter(node => node.tagName === "DETAILS");
    for (const item of details) {
      if (!item.open && page !== "dashboard") {
        item.replaceChildren(item.querySelector("summary"));
      }
      item.open = true;
    }
    for (const node of clone.querySelectorAll("button, a, label")) {
      const label = document.createElement("span");
      label.className = node.className;
      label.append(...node.childNodes);
      node.replaceWith(label);
    }
    root.append(clone);
  }
  for (const node of root.querySelectorAll("*")) {
    if (node.namespaceURI !== root.namespaceURI) continue;
    for (const name of node.getAttributeNames()) {
      if (!["class", "id", "style", "src", "open"].includes(name)) node.removeAttribute(name);
    }
    node.classList.remove("reveal-pending", "reveal-in");
    node.style.removeProperty("--reveal-delay");
    if (!node.style.length) node.removeAttribute("style");
  }
}

async function renderPng(root, css, width, height) {
  // Aim for 2× text resolution. Keep large matrices inside browser canvas limits.
  const scale = Math.min(2, 16384 / Math.max(width, height), Math.sqrt(32_000_000 / (width * height)));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.floor(width * scale));
  canvas.height = Math.max(1, Math.floor(height * scale));
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", canvas.width);
  svg.setAttribute("height", canvas.height);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const style = document.createElementNS(svg.namespaceURI, "style");
  style.textContent = css;
  const panel = document.createElementNS(svg.namespaceURI, "foreignObject");
  panel.setAttribute("width", width);
  panel.setAttribute("height", height);
  panel.append(root);
  svg.append(style, panel);
  const image = new Image();
  image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(svg));
  await image.decode();
  const context = canvas.getContext("2d", { alpha: false });
  context.drawImage(image, 0, 0);
  return new Promise((resolve, reject) => canvas.toBlob(blob => {
    if (blob) resolve(blob);
    else reject(new Error("Could not create the PNG image."));
  }, "image/png"));
}

async function capture(page) {
  const root = document.createElement("div");
  root.className = "capture-root capture-" + page;
  const title = document.createElement("h1");
  title.textContent = document.querySelector(".page-heading h1").textContent;
  root.append(title);
  const label = caption(page);
  if (label) {
    const note = document.createElement("p");
    note.className = "capture-caption";
    note.textContent = label;
    root.append(note);
  }
  collectPanels(page, root);
  const stage = document.createElement("iframe");
  stage.className = "capture-stage";
  stage.inert = true;
  document.body.append(stage);
  let png;
  try {
    const frame = stage.contentDocument;
    frame.open();
    frame.write("<!doctype html><html><head></head><body></body></html>");
    frame.close();
    const style = frame.createElement("style");
    style.textContent = Array.from(document.styleSheets).filter(sheet => !sheet.href?.endsWith("/responsive.css")).map(sheet =>
      Array.from(sheet.cssRules, rule => rule.cssText).join("\n")
    ).join("\n");
    style.textContent += ":root { scrollbar-gutter: auto; overflow: hidden; }";
    frame.head.append(style);
    frame.body.append(root);
    // Size to the actual panels, including the last column of a scrolling table.
    const initialWidth = root.getBoundingClientRect().width;
    let width = Math.max(initialWidth, root.scrollWidth);
    for (const item of root.querySelectorAll(".table-scroll, .formula")) {
      width = Math.max(width, initialWidth + item.scrollWidth - item.clientWidth);
    }
    width = Math.ceil(width);
    stage.style.width = width + "px";
    root.style.width = width + "px";
    const height = Math.ceil(root.getBoundingClientRect().height);
    png = await renderPng(root, style.textContent, width, height);
  } finally {
    stage.remove();
  }
  const query = new URLSearchParams({ label: Array.from(label).slice(0, 60).join("") });
  const response = await fetch("api/screenshots/" + page + "?" + query, {
    method: "POST", headers: { "Content-Type": "image/png" }, body: png,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Screenshot could not be saved.");
  return result.name;
}

export function enableScreenshots(page, toast) {
  const button = document.getElementById("screenshot");
  if (!button) return;
  button.disabled = false;
  button.addEventListener("click", async () => {
    if (document.getElementById("search-button")?.disabled) {
      toast("Wait for the query results, then take a screenshot.");
      return;
    }
    button.disabled = true;
    button.textContent = "Saving…";
    document.getElementById("toast").hidden = true;
    try {
      const filename = await capture(page);
      toast("Saved to screenshots/" + filename);
    } catch (error) {
      toast(error.message);
    } finally {
      button.textContent = "Screenshot";
      button.disabled = false;
    }
  });
}
