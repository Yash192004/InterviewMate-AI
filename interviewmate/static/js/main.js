/* main.js – Shared utilities, sidebar toggle, chart init */

// ── Sidebar Toggle ────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const menuBtn = document.getElementById("menuBtn");

  if (menuBtn) {
    menuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      overlay.classList.toggle("show");
    });
  }
  if (overlay) {
    overlay.addEventListener("click", () => {
      sidebar.classList.remove("open");
      overlay.classList.remove("show");
    });
  }
});

// ── Dashboard Charts ──────────────────────────────────────────
function initDashboardCharts(scores, dates, skillLabels, skillValues) {
  const defaultColors = [
    "#4f46e5","#10b981","#f59e0b","#ef4444","#8b5cf6",
    "#06b6d4","#ec4899","#84cc16","#f97316","#6366f1",
  ];

  // Progress Line Chart
  const progressCtx = document.getElementById("progressChart");
  if (progressCtx) {
    new Chart(progressCtx, {
      type: "line",
      data: {
        labels: scores.length ? dates : ["No data"],
        datasets: [{
          label: "Interview Score",
          data: scores.length ? scores : [0],
          fill: true,
          backgroundColor: "rgba(79,70,229,.08)",
          borderColor: "#4f46e5",
          borderWidth: 2.5,
          pointBackgroundColor: "#4f46e5",
          pointRadius: 5,
          pointHoverRadius: 7,
          tension: 0.4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 10, ticks: { stepSize: 2, font: { size: 11 } }, grid: { color: "#f0f2f8" } },
          x: { ticks: { font: { size: 11 } }, grid: { display: false } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `Score: ${ctx.raw}/10` } },
        },
      },
    });
  }

  // Skills Radar / Bar Chart
  const skillsCtx = document.getElementById("skillsChart");
  if (skillsCtx) {
    if (skillLabels.length >= 3) {
      new Chart(skillsCtx, {
        type: "radar",
        data: {
          labels: skillLabels,
          datasets: [{
            label: "Avg Score",
            data: skillValues,
            borderColor: "#4f46e5",
            backgroundColor: "rgba(79,70,229,.15)",
            borderWidth: 2,
            pointBackgroundColor: "#4f46e5",
            pointRadius: 4,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { r: { min: 0, max: 10, ticks: { stepSize: 2, font: { size: 10 } } } },
          plugins: { legend: { display: false } },
        },
      });
    } else {
      new Chart(skillsCtx, {
        type: "bar",
        data: {
          labels: skillLabels.length ? skillLabels : ["No data yet"],
          datasets: [{
            label: "Score",
            data: skillValues.length ? skillValues : [0],
            backgroundColor: defaultColors.slice(0, skillValues.length || 1),
            borderRadius: 6,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { min: 0, max: 10, ticks: { stepSize: 2, font: { size: 11 } }, grid: { color: "#f0f2f8" } },
            x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          },
          plugins: { legend: { display: false } },
        },
      });
    }
  }
}

// ── Results Charts ────────────────────────────────────────────
function initResultsCharts(overallScore, labels, values) {
  // Donut score chart
  const donutCtx = document.getElementById("scoreDonut");
  if (donutCtx) {
    const pct = Math.round((overallScore / 10) * 100);
    new Chart(donutCtx, {
      type: "doughnut",
      data: {
        datasets: [{
          data: [pct, 100 - pct],
          backgroundColor: [scoreColor(overallScore), "#f0f2f8"],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: false,
        cutout: "74%",
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
      },
    });
  }

  // Breakdown bar chart
  const breakdownCtx = document.getElementById("breakdownChart");
  if (breakdownCtx && labels.length) {
    new Chart(breakdownCtx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Score",
          data: values,
          backgroundColor: values.map(v => scoreColor(v) + "cc"),
          borderColor: values.map(v => scoreColor(v)),
          borderWidth: 1.5,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        scales: {
          x: { min: 0, max: 10, grid: { color: "#f0f2f8" }, ticks: { stepSize: 2 } },
          y: { grid: { display: false }, ticks: { font: { size: 12 } } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `${ctx.raw}/10` } },
        },
      },
    });
  }
}

function scoreColor(score) {
  if (score >= 7.5) return "#10b981";
  if (score >= 5)   return "#f59e0b";
  return "#ef4444";
}

// ── Jinja filter shim (for from_json in templates) ────────────
// (not needed in JS – used via Jinja2 custom filter in Flask)
