// Restore the shell before the new page paints, including during back/forward navigation.
try {
  document.documentElement.classList.toggle("sidebar-collapsed", sessionStorage.getItem("sidebar-collapsed") === "true");
} catch {
  // Storage may be unavailable in private browsing.
}
