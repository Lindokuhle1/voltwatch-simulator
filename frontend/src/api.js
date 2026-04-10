const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:5000";

export async function getLatestTelemetry() {
  const response = await fetch(`${API_BASE}/api/telemetry/latest`);
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export async function getTelemetryHistory(limit = 20, deviceId = "") {
  const params = new URLSearchParams({ limit: String(limit) });
  if (deviceId) {
    params.set("device_id", deviceId);
  }
  const response = await fetch(`${API_BASE}/api/telemetry/history?${params.toString()}`);
  if (!response.ok) {
    return { items: [] };
  }
  return response.json();
}

export async function getBatteryStatus(deviceId = "") {
  const params = new URLSearchParams();
  if (deviceId) {
    params.set("device_id", deviceId);
  }
  const query = params.toString();
  const response = await fetch(
    `${API_BASE}/api/battery/status${query ? `?${query}` : ""}`
  );
  if (!response.ok) {
    return { health: "UNKNOWN", latest: null };
  }
  return response.json();
}

export async function getBatteries(limit = 100) {
  const response = await fetch(`${API_BASE}/api/batteries?limit=${limit}`);
  if (!response.ok) {
    return { items: [] };
  }
  return response.json();
}

export async function getBatteryDailySummary(deviceId, date) {
  const params = new URLSearchParams({ device_id: deviceId, date });
  const response = await fetch(`${API_BASE}/api/battery/daily-summary?${params.toString()}`);
  if (!response.ok) {
    return {
      device_id: deviceId,
      date,
      samples: 0,
      trips: 0,
      operating_hours: 0,
      idle_hours: 0,
      charging_hours: 0,
    };
  }
  return response.json();
}

export async function downloadMonthlyReport(month, deviceId = "") {
  const params = new URLSearchParams();
  if (month) {
    params.set("month", month);
  }
  if (deviceId) {
    params.set("device_id", deviceId);
  }

  const response = await fetch(`${API_BASE}/api/reports/monthly?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Failed to export monthly report");
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  const suffix = deviceId || "all_batteries";
  link.href = url;
  link.download = `voltwatch_monthly_report_${month}_${suffix}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
