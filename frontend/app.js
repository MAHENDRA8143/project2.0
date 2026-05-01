const API_BASE = "/api";

// Scale up the base HTML font size to make text more readable
document.documentElement.style.fontSize = "115%";

// Set the browser tab title
document.title = "Smart Waste Water Prediction Treatment";

// Increase default font size for the graphs if Chart.js is loaded
if (typeof Chart !== "undefined") {
  Chart.defaults.font.size = 14;
}

let token = "";
let role = "";
let loadChart;
let phChart;
let nutrientChart;
let homeTrendChart;
let latestRecords = [];
let latestPredictions = [];
let latestSevenDayPredictions = [];
let refreshTimer = null;
let isDashboardLoading = false;
let forecastVisible = false;

const loginSection = document.getElementById("loginSection");
const dashboardSection = document.getElementById("dashboardSection");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const logoutBtn = document.getElementById("logoutBtn");
const dataTable = document.getElementById("dataTable");
const alertsPanel = document.getElementById("alertsPanel");
const forecastPanel = document.getElementById("forecastPanel");
const forecastPanelWrap = document.getElementById("forecastPanelWrap");
const toggleForecastBtn = document.getElementById("toggleForecastBtn");
const systemStatus = document.getElementById("systemStatus");
const lastUpdated = document.getElementById("lastUpdated");
const modal = document.getElementById("detailedAlertModal");
const modalContent = document.getElementById("detailedAlertContent");

const thresholds = {
  BOD: { unit: "mg/L", safe: "< 30", warning: 30, critical: 50 },
  COD: { unit: "mg/L", safe: "< 250", warning: 250, critical: 400 },
  pH: { unit: "", safe: "6.5 - 8.5", low: 6.5, high: 8.5, criticalLow: 6.0, criticalHigh: 9.0 },
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

function authHeaders() {
  return { Authorization: `Bearer ${token}` };
}

function formatDate(ts) {
  const date = new Date(ts);
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: IST_TIMEZONE,
    year: "numeric",
    month: "long",
    day: "2-digit",
  }).formatToParts(date);
  
  const p = {};
  for (const part of parts) p[part.type] = part.value;
  
  return `${p.day}-${p.month}, ${p.year}`;
}

function formatTime(ts) {
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(ts));
}

function formatTimeRange(ts) {
  const start = new Date(ts);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return `${formatTime(start)}-${formatTime(end)}`;
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
    if (value <= config.criticalLow || value >= config.criticalHigh) return "critical";
    if (value < config.low || value > config.high) return "warning";
    return "normal";
  }

  if (config.inverse) {
    if (value <= config.critical) return "critical";
    if (value <= config.warning) return "warning";
    return "normal";
  }

  if (value >= config.critical) return "critical";
  if (value >= config.warning) return "warning";
  return "normal";
}

function rowStatus(record) {
  const statuses = ["BOD", "COD", "pH", "DO", "NH3_N", "TP"].map((metric) => getMetricStatus(metric, record[metric]));
  if (statuses.includes("critical")) return "critical";
  if (statuses.includes("warning")) return "warning";
  return "normal";
}

function getProblem(metric, value) {
  const status = getMetricStatus(metric, value);
  const val = Number(value);

  if (status === "normal") {
    return {
      description: `${metricLabel(metric)} is within the optimal operating range. Treatment processes are stable.`,
      actions: ["Continue routine automated monitoring.", "Maintain current setpoints and dosing rates."],
    };
  }

  if (metric === "pH") {
    const isAcidic = val < 6.5;
    if (status === "critical") {
      return isAcidic
        ? {
            description: "Severe acidic shock. Immediate risk of biological floc destruction and toxic gas release.",
            actions: ["Dose caustic soda (NaOH) or lime immediately.", "Halt acidic sidestreams or industrial feeds.", "Check anaerobic digester supernatant return for VFA accumulation."]
          }
        : {
            description: "Severe alkaline shock. High risk of nitrifier die-off and poor sludge settling.",
            actions: ["Dose acid (e.g., sulfuric or hydrochloric) to neutralize.", "Investigate industrial cleaning/CIP discharges.", "Isolate alkaline influent if possible."]
          };
    } else {
      return isAcidic
        ? {
            description: "Mild acidic condition detected. Could gradually suppress nitrification.",
            actions: ["Monitor alkalinity levels and influent pH trends.", "Check chemical dosing pumps for leaks."]
          }
        : {
            description: "Mild alkaline condition. Ammonia toxicity to bacteria may increase.",
            actions: ["Monitor influent pH trends closely.", "Check alkaline chemical dosing setpoints."]
          };
    }
  }

  if (metric === "DO") {
    if (status === "critical") {
      return {
        description: "Critical low dissolved oxygen. High risk of filamentous bulking, foul odors, and poor effluent quality.",
        actions: ["Run standby blowers at maximum capacity immediately.", "Check for sudden COD/BOD shock loads depleting oxygen.", "Verify diffusers are not blocked or damaged."]
      };
    } else {
      return {
        description: "Dissolved oxygen is trending low. Aeration may be insufficient for the current organic load.",
        actions: ["Increase variable frequency drive (VFD) speed on blowers.", "Verify DO sensor calibration.", "Inspect tank for dead mixing zones."]
      };
    }
  }

  if (metric === "BOD") {
    if (status === "critical") {
      return {
        description: "Severe organic overload detected. High risk of biological system failure and effluent violation.",
        actions: ["Maximize aeration immediately.", "Consider diverting influent to equalization basin.", "Increase return activated sludge (RAS) rate.", "Check for illicit industrial discharges."]
      };
    } else {
      return {
        description: "Moderate organic load increase. Biological treatment capacity is being stretched.",
        actions: ["Verify aeration rates match the increased load.", "Check primary clarifier sludge levels.", "Sample influent for unexpected high-strength waste."]
      };
    }
  }

  if (metric === "COD") {
    if (status === "critical") {
      return {
        description: "Critical COD spike. Probable toxic or heavy industrial discharge entering the plant.",
        actions: ["Isolate toxic influent to emergency holding tanks if possible.", "Dose powdered activated carbon (PAC) to adsorb recalcitrant organics.", "Protect bioreactor by increasing biomass inventory."]
      };
    } else {
      return {
        description: "Elevated chemical oxygen demand indicating higher non-biodegradable or industrial load.",
        actions: ["Monitor BOD/COD ratio for toxicity indicators.", "Check coagulation/flocculation dosing in primary treatment.", "Prepare for potential downstream impact on UV/chlorine disinfection."]
      };
    }
  }

  if (metric === "NH3_N") {
    if (status === "critical") {
      return {
        description: "Critical ammonia breakthrough. Toxic conditions for receiving waters and aquatic life.",
        actions: ["Maximize aeration to vigorously boost nitrifying bacteria.", "Dose alkalinity (e.g., sodium carbonate) if pH is dropping.", "Reduce influent flow to increase biological contact time."]
      };
    } else {
      return {
        description: "Elevated ammonia levels. Nitrification efficiency is starting to degrade.",
        actions: ["Check aeration (DO) levels, as nitrification requires high oxygen.", "Verify pH and alkalinity are sufficient (> 7.0 pH ideally).", "Consider increasing sludge age (SRT)."]
      };
    }
  }

  if (metric === "TP") {
    if (status === "critical") {
      return {
        description: "Severe phosphorus discharge violation risk. Biological or chemical removal failure detected.",
        actions: ["Immediately manually increase chemical precipitation (alum/ferric) dosing.", "Waste more sludge to remove phosphorus-rich biomass.", "Check for anaerobic conditions in clarifiers causing phosphorus release."]
      };
    } else {
      return {
        description: "Phosphorus levels are rising. Biological uptake or chemical precipitation is sub-optimal.",
        actions: ["Adjust metal salt coagulant dosing.", "Check anaerobic zone for proper volatile fatty acid (VFA) levels.", "Monitor sludge blanket depth in secondary clarifier."]
      };
    }
  }

  return {
    description: `${metricLabel(metric)} is abnormal.`,
    actions: ["Review operator logs.", "Verify sensor health."]
  };
}

function metricLabel(metric) {
  return metric === "NH3_N" ? "NH3-N" : metric;
}

function alertFromPoint(metric, record, source = record.__source === "prediction" ? "AI Forecast" : "Real-time Measurement") {
  const value = Number(record[metric]);
  const status = getMetricStatus(metric, value);
  const config = thresholds[metric];
  const problem = getProblem(metric, value);

  return {
    metric,
    value,
    status,
    safeRange: `${config.safe}${config.unit ? ` ${config.unit}` : ""}`,
    timestamp: record.timestamp,
    source,
    description: problem.description,
    actions: problem.actions,
  };
}

function withSource(records, source) {
  return records.map((record) => ({ ...record, __source: source }));
}

function lastDailyRows(records, count = 4) {
  const byDate = new Map();
  records.forEach((record) => {
    byDate.set(formatDate(record.timestamp), record);
  });
  return Array.from(byDate.values()).slice(-count);
}

function renderTable(actualRows, predictions) {
  const rows = [...withSource(actualRows, "data"), ...withSource(predictions, "prediction")];
  const metricCellClass = (metric, record) => {
    const status = getMetricStatus(metric, record[metric]);
    return status === "normal" ? "" : ` anomaly-cell ${status}`;
  };
  const metricCellAttrs = (metric, record) => {
    const status = getMetricStatus(metric, record[metric]);
    return status === "normal" ? "" : ` data-alert-metric="${metric}"`;
  };
  const metricCellContent = (metric, record, digits = 1) => {
    const status = getMetricStatus(metric, record[metric]);
    const value = formatValue(record[metric], digits);
    return status === "normal" ? value : `<span class="openable-value">${value}<span class="open-icon">i</span></span>`;
  };

  dataTable.innerHTML = rows
    .map((record) => {
      const status = rowStatus(record);
      const rowKey = `${record.__source}-${record.timestamp}`;
      return `
        <tr class="${status !== "normal" ? `row-${status}` : ""} ${record.__source === "prediction" ? "prediction-row" : ""}">
          <td>${formatDate(record.timestamp)}</td>
          <td>${formatTimeRange(record.timestamp)}</td>
          <td><span class="source-chip ${record.__source}">${record.__source === "prediction" ? "Prediction" : "Data"}</span></td>
          <td class="${metricCellClass("BOD", record)}" data-row-key="${rowKey}"${metricCellAttrs("BOD", record)}>${metricCellContent("BOD", record)}</td>
          <td class="${metricCellClass("COD", record)}" data-row-key="${rowKey}"${metricCellAttrs("COD", record)}>${metricCellContent("COD", record)}</td>
          <td class="${metricCellClass("pH", record)}" data-row-key="${rowKey}"${metricCellAttrs("pH", record)}>${metricCellContent("pH", record)}</td>
          <td class="${metricCellClass("DO", record)}" data-row-key="${rowKey}"${metricCellAttrs("DO", record)}>${metricCellContent("DO", record)}</td>
          <td class="${metricCellClass("NH3_N", record)}" data-row-key="${rowKey}"${metricCellAttrs("NH3_N", record)}>${metricCellContent("NH3_N", record)}</td>
          <td class="${metricCellClass("TP", record)}" data-row-key="${rowKey}"${metricCellAttrs("TP", record)}>${metricCellContent("TP", record, 2)}</td>
        </tr>
      `;
    })
    .join("");

  const rowLookup = new Map(rows.map((record) => [`${record.__source}-${record.timestamp}`, record]));
  dataTable.querySelectorAll("[data-alert-metric]").forEach((cell) => {
    cell.addEventListener("click", () => {
      const record = rowLookup.get(cell.dataset.rowKey);
      if (record) {
        showDetailedAlert(alertFromPoint(cell.dataset.alertMetric, record));
      }
    });
  });
}

function renderAlerts(records) {
  const latest = records[records.length - 1];
  if (!latest) {
    alertsPanel.innerHTML = "";
    systemStatus.textContent = "No Data";
    systemStatus.className = "status-pill warning";
    return;
  }

  const metrics = ["BOD", "COD", "pH", "DO", "NH3_N", "TP"];
  const cards = metrics.map((metric) => {
    let targetRecord = latest;
    let maxSeverity = 0; // 0: normal, 1: warning, 2: critical

    for (const record of records) {
      const status = getMetricStatus(metric, record[metric]);
      const severity = status === "critical" ? 2 : status === "warning" ? 1 : 0;
      if (severity >= maxSeverity && severity > 0) {
        maxSeverity = severity;
        targetRecord = record;
      }
    }
    return alertFromPoint(metric, targetRecord);
  });
  const activeCards = cards.filter((card) => card.status !== "normal");
  const hasProblem = activeCards.length > 0;

  systemStatus.textContent = hasProblem ? "Action Needed" : "All Normal";
  systemStatus.className = `status-pill ${hasProblem ? "critical" : "normal"}`;

  const alertsTab = document.querySelector('.tab-btn[data-view="alerts"]');
  if (alertsTab) {
    alertsTab.classList.remove("alert-active", "alert-safe");
    alertsTab.classList.add(hasProblem ? "alert-active" : "alert-safe");
  }

  if (!hasProblem) {
    alertsPanel.innerHTML = '<div class="forecast-empty" style="grid-column: 1 / -1; text-align: center; border-color: var(--green-line); color: var(--green); background: var(--green-soft);">No active warnings or critical alerts. System is operating optimally.</div>';
  } else {
    alertsPanel.innerHTML = activeCards
      .map((card) => `
        <button class="system-alert ${card.status}" type="button" data-metric="${card.metric}">
          <span class="alert-icon">!</span>
          <span>
            <strong>${metricLabel(card.metric)}</strong>
            <small>Value: ${formatValue(card.value, card.metric === "pH" ? 2 : 1)} ${thresholds[card.metric].unit} at ${formatTime(card.timestamp)}</small>
            <small>Safe Range: ${card.safeRange}</small>
          </span>
          <em>${card.status}</em>
        </button>
      `)
      .join("");

    alertsPanel.querySelectorAll(".system-alert").forEach((button) => {
      button.addEventListener("click", () => {
        const metric = button.dataset.metric;
        const cardData = activeCards.find((c) => c.metric === metric);
        if (cardData) showDetailedAlert(cardData);
      });
    });
  }
}

function groupForecastByDay(predictions) {
  const days = new Map();

  for (const record of predictions) {
    const timestamp = new Date(record.timestamp);
    const dayLabel = new Intl.DateTimeFormat("en-US", {
      timeZone: IST_TIMEZONE,
      weekday: "short",
      month: "short",
      day: "numeric",
    }).format(timestamp);

    if (!days.has(dayLabel)) {
      days.set(dayLabel, []);
    }

    days.get(dayLabel).push(record);
  }

  return Array.from(days.entries()).map(([dayLabel, records]) => ({ dayLabel, records }));
}

function extendToSevenDays(predictions) {
  if (!predictions.length) return [];

  const base = predictions.slice(0, 24);
  const extended = [];

  for (let dayOffset = 0; dayOffset < 7; dayOffset += 1) {
    for (let hourIndex = 0; hourIndex < base.length; hourIndex += 1) {
      const record = base[hourIndex];
      const timestamp = new Date(record.timestamp);
      timestamp.setDate(timestamp.getDate() + dayOffset);

      const drift = 1 + dayOffset * 0.018;
      const doDrift = Math.max(0.75, 1 - dayOffset * 0.012);

      const forecastRecord = {
        ...record,
        timestamp: timestamp.toISOString(),
        hour_label: formatTime(timestamp),
        day_label: new Intl.DateTimeFormat("en-US", {
          timeZone: IST_TIMEZONE,
          weekday: "short",
          month: "short",
          day: "numeric",
        }).format(timestamp),
        day_index: dayOffset + 1,
        BOD: Number((Number(record.BOD) * drift).toFixed(2)),
        COD: Number((Number(record.COD) * drift).toFixed(2)),
        pH: Number(record.pH),
        DO: Number((Number(record.DO) * doDrift).toFixed(2)),
        NH3_N: Number((Number(record.NH3_N) * drift).toFixed(2)),
        TP: Number((Number(record.TP) * drift).toFixed(2)),
        condition: record.condition || "safe",
      };

      extended.push(forecastRecord);
    }
  }

  return extended;
}

function forecastConditionFromRecord(record) {
  const statuses = ["BOD", "COD", "pH", "DO", "NH3_N", "TP"].map((metric) => getMetricStatus(metric, record[metric]));
  if (statuses.includes("critical")) return "critical";
  if (statuses.includes("warning")) return "warning";
  return "safe";
}

function buildTwentyFourHourForecast(records) {
  const seededRecords = records.slice(0, 24);
  if (!seededRecords.length) return [];
  if (seededRecords.length >= 24) return seededRecords;

  const first = seededRecords[0];
  const last = seededRecords[seededRecords.length - 1] || first;
  const start = new Date(first.timestamp);
  const values = ["BOD", "COD", "pH", "DO", "NH3_N", "TP"];

  return Array.from({ length: 24 }, (_unused, hourIndex) => {
    const source = seededRecords[Math.min(hourIndex, seededRecords.length - 1)];
    const timestamp = new Date(start);
    timestamp.setHours(timestamp.getHours() + hourIndex);

    const blend = seededRecords.length > 1 ? hourIndex / 23 : hourIndex / 23;
    const forecastRecord = { ...source, timestamp: timestamp.toISOString(), hour_label: formatTime(timestamp) };

    values.forEach((metric) => {
      const startValue = Number(first[metric]);
      const endValue = Number(last[metric]);
      const baseValue = seededRecords.length > 1
        ? startValue + (endValue - startValue) * blend
        : startValue;
      const drift = metric === "DO"
        ? Math.max(0.7, 1 - hourIndex * 0.01)
        : 1 + hourIndex * 0.008;

      forecastRecord[metric] = Number((baseValue * drift).toFixed(metric === "pH" ? 2 : 2));
    });

    forecastRecord.condition = forecastConditionFromRecord(forecastRecord);
    return forecastRecord;
  });
}

function renderSevenDayForecast(predictions) {
  if (!forecastPanel) return;

  if (!predictions.length) {
    forecastPanel.innerHTML = '<div class="forecast-empty">No 7-day forecast available from the backend yet. Reload after the API is available.</div>';
    return;
  }

  const groupedDays = groupForecastByDay(predictions).slice(0, 7);

  forecastPanel.innerHTML = groupedDays
    .map(({ dayLabel, records }, index) => {
      const bodValues = records.map((record) => Number(record.BOD));
      const codValues = records.map((record) => Number(record.COD));
      const doValues = records.map((record) => Number(record.DO));
      const phValues = records.map((record) => Number(record.pH));
      const conditionCounts = records.reduce((counts, record) => {
        const condition = record.condition || "safe";
        counts[condition] = (counts[condition] || 0) + 1;
        return counts;
      }, {});

      const severity = conditionCounts.critical ? "critical" : conditionCounts.warning ? "warning" : "safe";
      const peakHour = records.reduce((best, record) => (Number(record.BOD) > Number(best.BOD) ? record : best), records[0]);

      return `
        <article class="forecast-day ${severity}" data-day-index="${index}">
          <div class="forecast-day-head">
            <div>
              <span class="forecast-day-index">Day ${index + 1}</span>
              <h4>${dayLabel}</h4>
            </div>
            <span class="forecast-badge ${severity}">${severity}</span>
          </div>

          <div class="forecast-metrics">
            <div><small>BOD avg</small><strong>${formatValue(bodValues.reduce((sum, value) => sum + value, 0) / bodValues.length)}</strong></div>
            <div><small>COD avg</small><strong>${formatValue(codValues.reduce((sum, value) => sum + value, 0) / codValues.length)}</strong></div>
            <div><small>DO avg</small><strong>${formatValue(doValues.reduce((sum, value) => sum + value, 0) / doValues.length)}</strong></div>
            <div><small>pH avg</small><strong>${formatValue(phValues.reduce((sum, value) => sum + value, 0) / phValues.length, 2)}</strong></div>
          </div>

          <div class="forecast-summary">
            <span><strong>Peak BOD</strong> ${formatValue(peakHour.BOD)} at ${peakHour.hour_label || formatTime(peakHour.timestamp)}</span>
            <span><strong>Condition</strong> ${peakHour.condition || "safe"}</span>
          </div>
        </article>
      `;
    })
    .join("");

  forecastPanel.querySelectorAll(".forecast-day").forEach((card) => {
    card.addEventListener("click", () => {
      const dayIndex = parseInt(card.dataset.dayIndex, 10);
      const dayData = groupedDays[dayIndex];
      showDailyForecastModal(dayData.dayLabel, dayData.records);
    });
  });
}

function toggleSevenDayForecast() {
  forecastVisible = !forecastVisible;

  if (forecastPanelWrap) {
    forecastPanelWrap.classList.toggle("hidden", !forecastVisible);
  }

  if (toggleForecastBtn) {
    toggleForecastBtn.textContent = forecastVisible ? "Hide 7-Day Forecast" : "Show 7-Day Forecast";
  }

  if (forecastVisible) {
    latestSevenDayPredictions = extendToSevenDays(latestPredictions);
    renderSevenDayForecast(latestSevenDayPredictions);
  }
}

function chartDataset(label, metric, records, color) {
  return {
    label,
    data: records.map((record) => Number(record[metric])),
    borderColor: color,
    backgroundColor: color,
    borderWidth: 2,
    tension: 0.3,
    pointRadius: records.map((record) => (getMetricStatus(metric, record[metric]) === "normal" ? 2.5 : 7)),
    pointHoverRadius: 9,
    pointBorderWidth: records.map((record) => (getMetricStatus(metric, record[metric]) === "normal" ? 1 : 4)),
    pointBorderColor: records.map((record) => {
      const status = getMetricStatus(metric, record[metric]);
      if (status === "critical") return "#ef4444";
      if (status === "warning") return "#ef4444";
      return color;
    }),
    pointBackgroundColor: records.map((record) => (getMetricStatus(metric, record[metric]) === "normal" ? color : "#351820")),
    segment: {
      borderDash: (context) => (records[context.p1DataIndex]?.__source === "prediction" ? [6, 5] : undefined),
    },
    metric,
  };
}

function buildChart(canvasId, records, datasets, yTitle) {
  const ctx = document.getElementById(canvasId);
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: records.map((record) => `${formatDate(record.timestamp)} ${formatTimeRange(record.timestamp)}`),
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "nearest", intersect: true },
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
            label: (context) => `${context.dataset.label}: ${formatValue(context.raw)}`,
          },
        },
      },
      scales: {
        x: {
          ticks: { autoSkip: false, color: chartTheme.tick, maxRotation: 50, minRotation: 50 },
          grid: { color: chartTheme.grid },
        },
        y: {
          ticks: { color: chartTheme.tick },
          title: { color: chartTheme.title, display: true, text: yTitle },
          grid: { color: chartTheme.grid },
        },
      },
      onClick: (_event, elements, activeChart) => {
        if (!elements.length) return;
        const element = elements[0];
        const dataset = activeChart.data.datasets[element.datasetIndex];
        const record = records[element.index];
        const status = getMetricStatus(dataset.metric, record[dataset.metric]);
        if (status !== "normal") {
          showDetailedAlert(alertFromPoint(dataset.metric, record));
        }
      },
    },
  });
}

function renderCharts(records) {
  if (loadChart) loadChart.destroy();
  if (phChart) phChart.destroy();
  if (nutrientChart) nutrientChart.destroy();

  loadChart = buildChart("loadChart", records, [
    chartDataset("BOD", "BOD", records, "#3b82f6"),
    chartDataset("COD", "COD", records, "#ef4444"),
  ], "mg/L");

  phChart = buildChart("phChart", records, [
    chartDataset("pH", "pH", records, "#14b8a6"),
  ], "pH");

  nutrientChart = buildChart("nutrientChart", records, [
    chartDataset("NH3-N", "NH3_N", records, "#8b5cf6"),
    chartDataset("TP", "TP", records, "#f97316"),
    chartDataset("DO", "DO", records, "#22c55e"),
  ], "mg/L");
}

function renderHomeCharts(records) {
  if (homeTrendChart) homeTrendChart.destroy();

  homeTrendChart = buildChart("homeTrendChart", records, [
    chartDataset("BOD", "BOD", records, "#3b82f6"),
    chartDataset("COD", "COD", records, "#ef4444"),
  ], "mg/L");
}

function showDetailedAlert(alert) {
  modal.querySelector(".modal-card").classList.remove("large");

  const statusText = alert.status === "critical" ? "Critical" : alert.status === "warning" ? "Warning" : "Normal";
  const actions = alert.actions.map((action) => `<li>${action}</li>`).join("");

  modalContent.innerHTML = `
    <div class="modal-header ${alert.status}">
      <div class="modal-title-row">
        <span class="modal-symbol">${alert.status === "critical" ? "!" : alert.status === "warning" ? "!" : "OK"}</span>
        <div>
          <h2 id="alertTitle">${statusText} Alert</h2>
          <p>${formatDate(alert.timestamp)} ${formatTimeRange(alert.timestamp)} IST</p>
        </div>
      </div>
      <button class="close-modal" type="button" aria-label="Close alert">x</button>
    </div>
    <div class="modal-body">
      <h3>Parameter Details</h3>
      <div class="param-grid">
        <div><small>Parameter</small><strong>${metricLabel(alert.metric)}</strong></div>
        <div><small>Current Value</small><strong class="${alert.status}">${formatValue(alert.value, alert.metric === "pH" ? 1 : 1)}</strong></div>
        <div><small>Safe Range</small><strong class="safe-text">${alert.safeRange}</strong></div>
        <div><small>Status</small><strong class="${alert.status}">${statusText.toUpperCase()}</strong></div>
      </div>

      <h3>Problem Description</h3>
      <p class="problem-box">${alert.description}</p>

      <h3>Recommended Actions</h3>
      <div class="actions-box">
        <strong>Immediate Actions:</strong>
        <ul>${actions}</ul>
      </div>
    </div>
    <div class="modal-footer">
      <button class="primary-btn close-alert" type="button">Close</button>
    </div>
  `;

  modal.classList.remove("hidden");
  modal.querySelector(".close-modal").addEventListener("click", closeModal);
  modal.querySelector(".close-alert").addEventListener("click", closeModal);
}

function showDailyForecastModal(dayLabel, records) {
  modal.querySelector(".modal-card").classList.add("large");

  const hourlyRecords = buildTwentyFourHourForecast(records);

  const rows = hourlyRecords.map((record) => {
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

  const average = (metric, digits = 1) => formatValue(hourlyRecords.reduce((sum, record) => sum + Number(record[metric]), 0) / hourlyRecords.length, digits);

  modalContent.innerHTML = `
    <div class="modal-header normal forecast-modal-header">
      <div class="modal-title-row">
        <span class="modal-symbol">i</span>
        <div>
          <h2 id="alertTitle">24-Hour Forecast</h2>
          <p>${dayLabel} · ${hourlyRecords.length} hourly points</p>
        </div>
      </div>
      <button class="close-modal" type="button" aria-label="Close modal">x</button>
    </div>
    <div class="modal-body forecast-modal-body">
      <div class="forecast-modal-summary">
        <div><small>BOD avg</small><strong>${average("BOD")}</strong></div>
        <div><small>COD avg</small><strong>${average("COD")}</strong></div>
        <div><small>DO avg</small><strong>${average("DO")}</strong></div>
        <div><small>pH avg</small><strong>${average("pH", 2)}</strong></div>
      </div>

      <div class="forecast-modal-table-wrap">
        <table class="forecast-modal-table">
          <thead>
            <tr>
              <th>Time</th><th>BOD</th><th>COD</th><th>pH</th><th>DO</th><th>NH3-N</th><th>TP</th><th>Status</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
    <div class="modal-footer forecast-modal-footer">
      <button id="exportDailyCsvBtn" class="primary-btn export-csv-btn" type="button">Export PDF</button>
      <button class="primary-btn close-alert" type="button">Close</button>
    </div>
  `;

  modal.classList.remove("hidden");
  modal.querySelector(".close-modal").addEventListener("click", closeModal);
  modal.querySelector(".close-alert").addEventListener("click", closeModal);
  modal.querySelector("#exportDailyCsvBtn").addEventListener("click", async () => {
    await exportDailyDataToPDF(dayLabel, hourlyRecords);
  });
}

function loadScriptOnce(src) {
  return new Promise((resolve, reject) => {
    const existing = Array.from(document.scripts).find((script) => script.src === src);
    if (existing) {
      if (existing.dataset.loaded === "true") {
        resolve(existing);
        return;
      }
      existing.addEventListener("load", () => resolve(existing), { once: true });
      existing.addEventListener("error", reject, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.addEventListener("load", () => {
      script.dataset.loaded = "true";
      resolve(script);
    }, { once: true });
    script.addEventListener("error", () => reject(new Error(`Failed to load ${src}`)), { once: true });
    document.head.appendChild(script);
  });
}

function buildReportRows(records) {
  return records.map((record) => [
    record.hour_label || formatTime(record.timestamp),
    formatValue(record.BOD),
    formatValue(record.COD),
    formatValue(record.pH, 2),
    formatValue(record.DO),
    formatValue(record.NH3_N),
    formatValue(record.TP, 2),
    record.condition ? record.condition.toUpperCase() : "SAFE",
  ]);
}

async function exportDailyDataToPDF(dayLabel, records) {
  const hourlyRecords = buildTwentyFourHourForecast(records);

  await loadScriptOnce("https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js");
  await loadScriptOnce("https://cdn.jsdelivr.net/npm/jspdf-autotable@3.8.4/dist/jspdf.plugin.autotable.min.js");

  if (!window.jspdf || !window.jspdf.jsPDF) {
    throw new Error("PDF library could not be loaded");
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const marginX = 14;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const reportTitle = "24-Hour Forecast Report";
  const generatedAt = new Intl.DateTimeFormat("en-IN", {
    timeZone: IST_TIMEZONE,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date());

  const averages = {
    BOD: formatValue(hourlyRecords.reduce((sum, record) => sum + Number(record.BOD), 0) / hourlyRecords.length),
    COD: formatValue(hourlyRecords.reduce((sum, record) => sum + Number(record.COD), 0) / hourlyRecords.length),
    DO: formatValue(hourlyRecords.reduce((sum, record) => sum + Number(record.DO), 0) / hourlyRecords.length),
    pH: formatValue(hourlyRecords.reduce((sum, record) => sum + Number(record.pH), 0) / hourlyRecords.length, 2),
  };
  const counts = hourlyRecords.reduce((acc, record) => {
    const key = (record.condition || "safe").toLowerCase();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, { safe: 0, warning: 0, critical: 0 });
  const peakRecord = hourlyRecords.reduce((best, record) => (Number(record.BOD) > Number(best.BOD) ? record : best), hourlyRecords[0]);

  doc.setFillColor(8, 13, 22);
  doc.rect(0, 0, pageWidth, 28, "F");
  doc.setTextColor(229, 237, 248);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.text("SMART WWTP", marginX, 15);
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text("Waste Water Prediction Treatment", marginX, 22);
  doc.setFontSize(16);
  doc.setFont("helvetica", "bold");
  doc.text(reportTitle, pageWidth - marginX, 14, { align: "right" });
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text(`Day: ${dayLabel}`, pageWidth - marginX, 20, { align: "right" });
  doc.text(`Generated: ${generatedAt} IST`, pageWidth - marginX, 25, { align: "right" });

  doc.setDrawColor(38, 52, 72);
  doc.setFillColor(16, 24, 38);
  doc.roundedRect(marginX, 35, pageWidth - (marginX * 2), 26, 3, 3, "FD");
  doc.setTextColor(229, 237, 248);
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text("Report Summary", marginX + 5, 42);
  doc.setFont("helvetica", "normal");
  doc.text(`24 hourly points | Safe: ${counts.safe} | Warning: ${counts.warning} | Critical: ${counts.critical}`, marginX + 5, 48);
  doc.text(`Averages - BOD: ${averages.BOD} mg/L | COD: ${averages.COD} mg/L | DO: ${averages.DO} mg/L | pH: ${averages.pH}`, marginX + 5, 54);
  doc.text(`Peak BOD: ${formatValue(peakRecord.BOD)} mg/L at ${peakRecord.hour_label || formatTime(peakRecord.timestamp)} | Peak condition: ${(peakRecord.condition || "safe").toUpperCase()}`, marginX + 5, 60);

  const tableRows = buildReportRows(hourlyRecords);
  doc.autoTable({
    head: [["Time", "BOD", "COD", "pH", "DO", "NH3-N", "TP", "Status"]],
    body: tableRows,
    startY: 69,
    margin: { left: marginX, right: marginX },
    theme: "grid",
    styles: {
      font: "helvetica",
      fontSize: 8.5,
      cellPadding: 2.6,
      overflow: "linebreak",
      valign: "middle",
      textColor: [16, 24, 38],
      lineColor: [38, 52, 72],
      lineWidth: 0.15,
    },
    headStyles: {
      fillColor: [23, 34, 51],
      textColor: [229, 237, 248],
      fontStyle: "bold",
    },
    alternateRowStyles: {
      fillColor: [245, 247, 250],
    },
    didParseCell: (data) => {
      if (data.section !== "body" || data.column.index !== 7) return;
      const status = String(data.cell.raw || "").toUpperCase();
      if (status === "CRITICAL") {
        data.cell.styles.fillColor = [251, 113, 133];
        data.cell.styles.textColor = [255, 255, 255];
      } else if (status === "WARNING") {
        data.cell.styles.fillColor = [251, 191, 36];
        data.cell.styles.textColor = [16, 24, 38];
      } else {
        data.cell.styles.fillColor = [52, 211, 153];
        data.cell.styles.textColor = [16, 24, 38];
      }
      data.cell.styles.fontStyle = "bold";
    },
    didDrawPage: (data) => {
      doc.setFontSize(8);
      doc.setTextColor(148, 163, 184);
      doc.text("Confidential operational summary for internal review.", marginX, pageHeight - 6);
      doc.text(`Page ${doc.getNumberOfPages()}`, pageWidth - marginX, pageHeight - 6, { align: "right" });
    },
  });

  const fileName = `forecast_${dayLabel.replace(/[^a-zA-Z0-9]/g, "_")}.pdf`;
  doc.save(fileName);
}

function closeModal() {
  modal.classList.add("hidden");
  modal.querySelector(".modal-card").classList.remove("large");
}

function renderHome(records) {
  const latest = records[records.length - 1];
  if (!latest) return;
  
  const metrics = ['BOD', 'COD', 'pH', 'DO'];
  metrics.forEach(metric => {
    const valElem = document.getElementById(`kpi-${metric.toLowerCase()}`);
    const statElem = document.getElementById(`kpi-${metric.toLowerCase()}-status`);
    if(valElem && statElem) {
      const val = latest[metric];
      const status = getMetricStatus(metric, val);
      
      valElem.textContent = formatValue(val, metric === 'pH' ? 2 : 1) + (thresholds[metric].unit ? ` ${thresholds[metric].unit}` : '');
      
      statElem.className = `kpi-status ${status === 'normal' ? 'safe' : status}`;
      statElem.textContent = status === 'normal' ? '✓ Optimal' : (status === 'warning' ? '⚠️ Warning' : '⚠ Critical');
    }
  });
  
  const hasProblem = metrics.some(m => getMetricStatus(m, latest[m]) !== 'normal');
  const heroStatus = document.getElementById('homeSystemStatus');
  if (heroStatus) {
    heroStatus.textContent = hasProblem ? "Action Needed" : "System Normal";
    heroStatus.className = `status-pill ${hasProblem ? "critical" : "normal"}`;
  }
}

function createWaterAnimation() {
  const canvas = document.createElement('canvas');

  // Style canvas to be a full page background
  canvas.style.position = 'fixed';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.width = '100vw';
  canvas.style.height = '100vh';
  canvas.style.zIndex = '-1'; // Behind everything
  canvas.style.opacity = '0.25'; // Subtle pollution effect
  canvas.style.pointerEvents = 'none'; // Prevent it from blocking clicks

  document.body.prepend(canvas);

  const ctx = canvas.getContext('2d');
  let particles = [];
  const particleCount = 120;

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    createParticles();
  }

  class Particle {
    constructor() {
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height;
      
      // Mix of floating toxic bubbles and sinking sludge
      this.isBubble = Math.random() > 0.5;
      this.vx = Math.random() * 0.6 - 0.3;
      // Bubbles rise, sludge sinks
      this.vy = this.isBubble ? -(Math.random() * 0.6 + 0.2) : (Math.random() * 0.4 + 0.1); 
      this.radius = this.isBubble ? Math.random() * 4 + 1.5 : Math.random() * 2.5 + 1;
      
      // Colors representing water pollution: Toxic Neon Green, Dark Sludge, Murky Grey
      const colors = [
        `rgba(57, 255, 20, ${Math.random() * 0.3 + 0.1})`,
        `rgba(101, 67, 33, ${Math.random() * 0.4 + 0.2})`,
        `rgba(80, 90, 80, ${Math.random() * 0.3 + 0.1})`
      ];
      this.color = colors[Math.floor(Math.random() * colors.length)];
    }

    update() {
      this.x += this.vx;
      this.y += this.vy;

      if (this.isBubble && this.y < -10) {
        this.y = canvas.height + 10;
        this.x = Math.random() * canvas.width;
      } else if (!this.isBubble && this.y > canvas.height + 10) {
        this.y = -10;
        this.x = Math.random() * canvas.width;
      }
    }

    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
      ctx.fillStyle = this.color;
      ctx.fill();
    }
  }

  function createParticles() {
    particles = [];
    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      p.update();
      p.draw();
    });
    requestAnimationFrame(animate);
  }

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();
  animate();
}

async function loadDashboard() {
  if (isDashboardLoading) return;
  isDashboardLoading = true;

  try {
    const [currentResp, predResp] = await Promise.all([
      fetch(`${API_BASE}/data/current?hours=96`, { headers: authHeaders() }),
      fetch(`${API_BASE}/predictions/next-day?history_hours=72`, { headers: authHeaders() }),
    ]);

    if (!currentResp.ok || !predResp.ok) {
      throw new Error("Dashboard data could not be loaded");
    }

    const currentData = await currentResp.json();
    const predData = await predResp.json();

    latestRecords = lastDailyRows(currentData.records || [], 4);
    latestPredictions = predData.predictions || [];
    const chartRecords = [...withSource(latestRecords, "data"), ...withSource(latestPredictions, "prediction")];

    renderTable(latestRecords, latestPredictions);
    renderAlerts(chartRecords);
    renderHome(latestRecords);
    if (forecastVisible) {
      latestSevenDayPredictions = extendToSevenDays(latestPredictions);
      renderSevenDayForecast(latestSevenDayPredictions);
    }
    if (document.getElementById("graphView").classList.contains("active")) {
      renderCharts(chartRecords);
    }
    renderHomeCharts(chartRecords);

    const last = chartRecords[chartRecords.length - 1];
    lastUpdated.textContent = last ? `Forecast Through: ${formatDate(last.timestamp)} ${formatTimeRange(last.timestamp)} IST` : "Forecast Through: no data";
  } finally {
    isDashboardLoading = false;
  }
}

function startHourlyRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    if (token) {
      loadDashboard().catch((error) => {
        loginError.textContent = error.message;
      });
    }
  }, 60 * 60 * 1000);
}

function transitionToDashboard() {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  dashboardSection.classList.remove("hidden");

  if (reduceMotion) {
    loginSection.classList.add("hidden");
    return Promise.resolve();
  }

  loginSection.classList.add("login-cover-open");
  dashboardSection.classList.add("dashboard-enter");

  return new Promise((resolve) => {
    window.setTimeout(() => {
      loginSection.classList.add("hidden");
      loginSection.classList.remove("login-cover-open");
      dashboardSection.classList.remove("dashboard-enter");
      resolve();
    }, 1550);
  });
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";

  try {
    const resp = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
      }),
    });

    if (!resp.ok) throw new Error("Login failed");

    const data = await resp.json();
    token = data.access_token;
    role = data.role;

    await Promise.all([
      transitionToDashboard(),
      loadDashboard(),
    ]);
    startHourlyRefresh();
  } catch (error) {
    loginError.textContent = error.message;
  }
});

logoutBtn.addEventListener("click", () => {
  token = "";
  role = "";
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  dashboardSection.classList.add("hidden");
  loginSection.classList.remove("hidden");
  loginSection.classList.remove("login-cover-open");
  dashboardSection.classList.remove("dashboard-enter");
});

document.querySelectorAll(".tab-btn").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(`${button.dataset.view}View`).classList.add("active");
    if (button.dataset.view === "graph") {
      const chartRecords = withSource(latestPredictions, "prediction");
      if (chartRecords.length) renderCharts(chartRecords);
      setTimeout(() => {
        if (loadChart) loadChart.resize();
        if (phChart) phChart.resize();
        if (nutrientChart) nutrientChart.resize();
      }, 0);
    }
  });
});

if (toggleForecastBtn) {
  toggleForecastBtn.addEventListener("click", toggleSevenDayForecast);
}

modal.addEventListener("click", (event) => {
  if (event.target === modal) closeModal();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeModal();
});

createWaterAnimation();
