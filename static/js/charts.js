// Chart.js is bundled locally so charts also work inside the offline executable.
const activeCharts = new Map();
export function barChart(
  id,
  labels,
  values,
  { horizontal = false, color = "#48c9b0", label = "Value", max } = {},
) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  activeCharts.get(id)?.destroy();
  const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  const chart = new window.Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label,
          data: values,
          backgroundColor: color,
          borderRadius: 4,
          barPercentage: 0.55,
          maxBarThickness: 22,
        },
      ],
    },
    options: {
      indexAxis: horizontal ? "y" : "x",
      responsive: true,
      maintainAspectRatio: false,
      animation: reduceMotion ? false : { duration: 250 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#20334b",
          padding: 12,
          callbacks: {
            label: (context) =>
              `${label}: ${Number(context.raw).toLocaleString("en", { maximumFractionDigits: 12 })}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: horizontal ? "#233247" : "transparent" },
          border: { display: false },
          ticks: { color: "#94a9c1", font: { size: 9 } },
          ...(horizontal
            ? {
                beginAtZero: true,
                max,
                title: {
                  display: true,
                  text: label,
                  color: "#94a9c1",
                  font: { size: 9 },
                },
              }
            : {}),
        },
        y: {
          grid: { color: horizontal ? "transparent" : "#233247" },
          border: { display: false },
          ticks: { color: "#94a9c1", font: { size: 9 }, precision: 0 },
          ...(!horizontal
            ? {
                beginAtZero: true,
                max,
                title: {
                  display: true,
                  text: label,
                  color: "#94a9c1",
                  font: { size: 9 },
                },
              }
            : {}),
        },
      },
    },
  });
  activeCharts.set(id, chart);
}
