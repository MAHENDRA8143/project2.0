// --- Reused constants and helpers from app.js ---
const thresholds = {
  BOD: { unit: "mg/L", safe: "< 30", warning: 30, critical: 50 },
  COD: { unit: "mg/L", safe: "< 250", warning: 250, critical: 400 },
  pH: { unit: "", safe: "6.5 - 8.5", low: 6.5, high: 8.5 },
  DO: { unit: "mg/L", safe: "> 5", warning: 5, critical: 3, inverse: true },
  NH3_N: { unit: "mg/L", safe: "< 10", warning: 10, critical: 15 },
  TP: { unit: "mg/L", safe: "< 4", warning: 4, critical: 6 },
};

const chartTheme = {
  grid: "#263448",
  tick: "#94a3b8",
  title: "#cbd5e1",
  legend: "#cbd5e1",
};

const IST_TIMEZONE = "Asia/Kolkata";

function formatTime(ts) {
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(ts));
}

function formatValue(value, digits = 1) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits).replace(/\.0$/, "") : "-";
}

function getMetricStatus(metric, rawValue) {
  const value = Number(rawValue);
  const config = thresholds[metric];
  if (!config || !Number.isFinite(value)) return "normal";

  if (metric === "pH") {
    return value < config.low || value > config.high ? "warning" : "normal";
  }

  if (config.inverse) {
    if (value < config.critical) return "critical";
    if (value < config.warning) return "warning";
    return "normal";
  }

  if (value > config.critical) return "critical";
  if (value > config.warning) return "warning";
  return "normal";
}

// --- Charting functions (adapted from app.js) ---
function chartDataset(label, metric, records, color) {
    return {
        label,
        data: records.map((record) => Number(record[metric])),
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 9,
        pointBorderWidth: 2,
        pointBorderColor: records.map((record) => {
          const status = getMetricStatus(metric, record[metric]);
          if (status === "critical" || status === "warning") return "#ef4444";
          return color;
        }),
        pointBackgroundColor: records.map((record) => (getMetricStatus(metric, record[metric]) === "normal" ? color : "#351820")),
        metric,
      };
}

function buildChart(canvasId, records, datasets, yAxes) {
    const ctx = document.getElementById(canvasId);
    return new Chart(ctx, {
      type: "line",
      data: {
        labels: records.map((record) => record.hour_label || formatTime(record.timestamp)),
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: chartTheme.legend, usePointStyle: true, boxWidth: 8 },
          },
          tooltip: {
            backgroundColor: "#101826",
            borderColor: "#263448",
            borderWidth: 1,
            titleColor: "#e5edf8",
            bodyColor: "#cbd5e1",
            callbacks: {
              label: (context) => `${context.dataset.label}: ${formatValue(context.raw, context.dataset.metric === 'pH' ? 2 : 1)}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: chartTheme.tick },
            grid: { color: chartTheme.grid },
            title: { display: true, text: 'Hour of Day (IST)', color: chartTheme.title }
          },
          ...yAxes
        },
      },
    });
}


// --- Page-specific logic ---
document.addEventListener("DOMContentLoaded", () => {
    // Match main app styles
    document.documentElement.style.fontSize = "115%";
    if (typeof Chart !== "undefined") {
        Chart.defaults.font.size = 14;
    }

    const dailyDataString = localStorage.getItem("dailyForecastData");
    if (!dailyDataString) {
        document.body.innerHTML = `<main class="dashboard-card" style="margin: 24px; text-align: center;"><h2>Error: No daily forecast data found.</h2><p>Please return to the main dashboard and click a forecast day again.</p></main>`;
        return;
    }

    const { dayLabel, records } = JSON.parse(dailyDataString);

    // Set title
    document.title = `Hourly Forecast for ${dayLabel} - SPECTRUM DYE WORKS`;
    document.getElementById("dailyViewTitle").textContent = `Hourly Forecast for ${dayLabel}`;

    // Render Table
    const tableBody = document.getElementById("dailyTable");
    tableBody.innerHTML = records.map((record) => {
        const time = record.hour_label || formatTime(record.timestamp);
        const statusClass = record.condition === "safe" ? "" : record.condition;
        const statusText = record.condition.charAt(0).toUpperCase() + record.condition.slice(1);

        return `
          <tr>
            <td>${time}</td>
            <td>${formatValue(record.BOD)}</td>
            <td>${formatValue(record.COD)}</td>
            <td>${formatValue(record.pH, 2)}</td>
            <td>${formatValue(record.DO)}</td>
            <td>${formatValue(record.NH3_N)}</td>
            <td>${formatValue(record.TP, 2)}</td>
            <td><span class="value-chip ${statusClass}">${statusText}</span></td>
          </tr>
        `;
      }).join("");

    // Render Charts
    buildChart("dailyLoadChart", records, [
        chartDataset("BOD", "BOD", records, "#3b82f6"),
        chartDataset("COD", "COD", records, "#ef4444"),
    ], { 
        y: {
            ticks: { color: chartTheme.tick },
            title: { color: chartTheme.title, display: true, text: "mg/L" },
            grid: { color: chartTheme.grid },
        }
    });

    const otherChart = buildChart("dailyOtherChart", records, [
        chartDataset("pH", "pH", records, "#14b8a6"),
        chartDataset("DO", "DO", records, "#22c55e"),
        chartDataset("NH3-N", "NH3_N", records, "#8b5cf6"),
        chartDataset("TP", "TP", records, "#f97316"),
    ], {
        y_mg: {
            type: 'linear',
            position: 'left',
            ticks: { color: chartTheme.tick },
            title: { color: chartTheme.title, display: true, text: "mg/L" },
            grid: { color: chartTheme.grid },
        },
        y_ph: {
            type: 'linear',
            position: 'right',
            ticks: { color: chartTheme.tick },
            title: { color: chartTheme.title, display: true, text: "pH" },
            grid: { drawOnChartArea: false }, // only show grid for left axis
            min: 6,
            max: 9,
        }
    });
    // Assign pH to the right axis
    otherChart.data.datasets.find(ds => ds.metric === 'pH').yAxisID = 'y_ph';
    otherChart.data.datasets.filter(ds => ds.metric !== 'pH').forEach(ds => ds.yAxisID = 'y_mg');
    otherChart.update();
});