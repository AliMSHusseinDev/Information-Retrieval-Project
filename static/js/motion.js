// Reveal each section once. Observe result lists as well, since searches replace their cards.
export function revealSections() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches || !window.IntersectionObserver) return;
  const main = document.getElementById("main");
  const selector = [
    ".hero", ".kpi", ".section-heading",
    ".chart-grid > article", ".pipeline-panel", "#main > details", ".index-layout article",
    ".analytics-panel", ".query-form", ".result-card", ".ranking-panel", ".math-step",
    ".export-card", "#main > .panel:not(.import-welcome)", ".empty-state",
  ].join(",");
  const seen = new WeakSet();
  const observer = new IntersectionObserver(entries => {
    let order = 0;
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const node = entry.target;
      observer.unobserve(node);
      node.style.setProperty("--reveal-delay", Math.min(order++, 4) * 45 + "ms");
      node.classList.replace("reveal-pending", "reveal-in");
      node.addEventListener("animationend", () => node.classList.remove("reveal-in"), { once: true });
    }
  });
  function watch(node) {
    if (seen.has(node)) return;
    seen.add(node);
    node.classList.add("reveal-pending");
    observer.observe(node);
  }
  main.querySelectorAll(selector).forEach(watch);
  const changes = new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        if (node.matches(selector)) watch(node);
        node.querySelectorAll(selector).forEach(watch);
      }
      for (const node of record.removedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        observer.unobserve(node);
        node.querySelectorAll(".reveal-pending").forEach(child => observer.unobserve(child));
      }
    }
  });
  // Replacing thousands of matrix cells should not trigger animation work.
  for (const id of ["math-content", "search-results", "kpi-grid", "export-grid"]) {
    const container = document.getElementById(id);
    if (container) changes.observe(container, { childList: true });
  }
}
