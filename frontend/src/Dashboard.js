import React, { useEffect, useMemo, useState } from "react";
import {
  downloadMonthlyReport,
  getBatteryAnalytics,
  getBatteryDailySummary,
  getBatteries,
  getBatteryStatus,
  getTelemetryHistory,
} from "./api";
import TelemetryChart from "./TelemetryChart";

function Dashboard() {
  const [status, setStatus] = useState({ health: "UNKNOWN", latest: null });
  const [history, setHistory] = useState([]);
  const [batteries, setBatteries] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [reportMonth, setReportMonth] = useState(new Date().toISOString().slice(0, 7));
  const [dailyDate, setDailyDate] = useState(new Date().toISOString().slice(0, 10));
  const [dailySummary, setDailySummary] = useState({
    operating_hours: 0,
    idle_hours: 0,
    charging_hours: 0,
    samples: 0,
  });
  const [analytics, setAnalytics] = useState(null);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    let mounted = true;

    const loadBatteries = async () => {
      const batteriesData = await getBatteries(200);
      if (!mounted) {
        return;
      }
      setBatteries((batteriesData.items || []).slice());
    };

    loadBatteries();
    const timer = setInterval(loadBatteries, 5000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!selectedDeviceId) {
      setStatus({ health: "UNKNOWN", latest: null });
      setHistory([]);
      setAnalytics(null);
      return;
    }

    let mounted = true;

    const loadSelectedBatteryData = async () => {
      const [statusData, historyData, analyticsData] = await Promise.all([
        getBatteryStatus(selectedDeviceId),
        getTelemetryHistory(25, selectedDeviceId),
        getBatteryAnalytics(selectedDeviceId),
      ]);
      const summaryData = await getBatteryDailySummary(selectedDeviceId, dailyDate);

      if (!mounted) {
        return;
      }
      setStatus(statusData);
      setHistory((historyData.items || []).slice().reverse());
      setAnalytics(analyticsData);
      setDailySummary(summaryData);
    };

    loadSelectedBatteryData();
    const timer = setInterval(loadSelectedBatteryData, 5000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [selectedDeviceId, dailyDate]);

  const latest = status.latest;

  const chartSeries = useMemo(() => {
    const labels = history.map((item) => {
      const date = new Date(item.timestamp);
      return date.toLocaleTimeString();
    });

    return {
      labels,
      voltage: history.map((item) => item.pack_voltage),
      current: history.map((item) => item.pack_current),
      temperature: history.map((item) => item.temperature),
    };
  }, [history]);

  const healthClass = `health-badge ${status.health.toLowerCase()}`;
  const selectedBattery = batteries.find((row) => row.device_id === selectedDeviceId) || null;
  const selectedCells = latest?.cell_voltages || [];
  const latitude = selectedBattery?.latitude ?? latest?.latitude ?? null;
  const longitude = selectedBattery?.longitude ?? latest?.longitude ?? null;
  const hasLocation = Number.isFinite(latitude) && Number.isFinite(longitude);
  const mapSrc = hasLocation
    ? `https://www.openstreetmap.org/export/embed.html?bbox=${Number(longitude) - 0.02}%2C${Number(latitude) - 0.02}%2C${Number(longitude) + 0.02}%2C${Number(latitude) + 0.02}&layer=mapnik&marker=${Number(latitude)}%2C${Number(longitude)}`
    : "";
  const selectedCellStats = useMemo(() => {
    if (!selectedCells.length) {
      return null;
    }

    const min = Math.min(...selectedCells);
    const max = Math.max(...selectedCells);
    const avg = selectedCells.reduce((sum, value) => sum + value, 0) / selectedCells.length;
    return { min, max, avg };
  }, [selectedCells]);

  const handleExport = async (deviceId = "") => {
    try {
      setIsExporting(true);
      await downloadMonthlyReport(reportMonth, deviceId);
    } catch (_error) {
      alert("Could not export report. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <main className="layout">
      <header className="topbar">
        <h1>VoltWatch Simulator</h1>
        {selectedDeviceId ? <div className={healthClass}>{status.health}</div> : null}
      </header>

      {!selectedDeviceId ? (
        <section className="table-wrap">
          <h2>Battery List</h2>
          <div className="report-controls">
            <label htmlFor="reportMonthAll">Report Month</label>
            <input
              id="reportMonthAll"
              type="month"
              value={reportMonth}
              onChange={(e) => setReportMonth(e.target.value)}
            />
            <button
              className="nav-btn"
              onClick={() => handleExport("")}
              disabled={isExporting}
            >
              {isExporting ? "Exporting..." : "Export Monthly Report (All Batteries)"}
            </button>
          </div>
          <p className="hint">Click a battery row to open its telemetry page.</p>
          <table>
            <thead>
              <tr>
                <th>Battery Serial</th>
                <th>State Of Charge</th>
                <th>Error_Count</th>
                <th>active</th>
                <th>cellIRmax</th>
                <th>lastActivityTime</th>
                <th>packVoltage</th>
                <th>packCurrent</th>
                <th>cycleCount</th>
                <th>health</th>
              </tr>
            </thead>
            <tbody>
              {batteries.map((row) => (
                <tr
                  key={row.device_id}
                  className="clickable-row"
                  onClick={() => setSelectedDeviceId(row.device_id)}
                >
                  <td>{row.device_id}</td>
                  <td>{row.soc.toFixed(1)}</td>
                  <td>{row.alarm_count}</td>
                  <td>{row.active ? "true" : "false"}</td>
                  <td>{row.cell_imbalance.toFixed(3)}</td>
                  <td>{new Date(row.last_activity).toLocaleString()}</td>
                  <td>{row.pack_voltage.toFixed(2)} V</td>
                  <td>{row.pack_current.toFixed(2)} A</td>
                  <td>{row.cycle_count}</td>
                  <td>
                    <span className={`mini-health ${row.health.toLowerCase()}`}>{row.health}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : (
        <>
          <section className="selected-strip">
            <span>Selected Battery:</span>
            <strong>{selectedDeviceId}</strong>
            <button className="nav-btn" onClick={() => setSelectedDeviceId("")}>Back To Battery List</button>
            <label htmlFor="dailyDate">Daily Summary Date</label>
            <input
              id="dailyDate"
              type="date"
              value={dailyDate}
              onChange={(e) => setDailyDate(e.target.value)}
            />
            <label htmlFor="reportMonthSingle">Month</label>
            <input
              id="reportMonthSingle"
              type="month"
              value={reportMonth}
              onChange={(e) => setReportMonth(e.target.value)}
            />
            <button
              className="nav-btn"
              onClick={() => handleExport(selectedDeviceId)}
              disabled={isExporting}
            >
              {isExporting ? "Exporting..." : "Export Monthly Report"}
            </button>
          </section>

          <section className="detail-wrap">
            <h2>Battery Details</h2>
            {selectedBattery ? (
              <>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span>Battery Serial</span>
                    <strong>{selectedBattery.device_id}</strong>
                  </div>
                  <div className="detail-item">
                    <span>Health</span>
                    <strong>{selectedBattery.health}</strong>
                  </div>
                  <div className="detail-item">
                    <span>State Of Charge</span>
                    <strong>{selectedBattery.soc.toFixed(1)}%</strong>
                  </div>
                  <div className="detail-item">
                    <span>Error_Count</span>
                    <strong>{selectedBattery.alarm_count}</strong>
                  </div>
                  <div className="detail-item">
                    <span>active</span>
                    <strong>{selectedBattery.active ? "true" : "false"}</strong>
                  </div>
                  <div className="detail-item">
                    <span>last Activity Time</span>
                    <strong>{new Date(selectedBattery.last_activity).toLocaleString()}</strong>
                  </div>
                  <div className="detail-item">
                    <span>Pack Voltage</span>
                    <strong>{selectedBattery.pack_voltage.toFixed(2)} V</strong>
                  </div>
                  <div className="detail-item">
                    <span>Pack Current</span>
                    <strong>{selectedBattery.pack_current.toFixed(2)} A</strong>
                  </div>
                  <div className="detail-item">
                    <span>temperature</span>
                    <strong>{selectedBattery.temperature.toFixed(2)} C</strong>
                  </div>
                  <div className="detail-item">
                    <span>cycleCount</span>
                    <strong>{selectedBattery.cycle_count}</strong>
                  </div>
                  <div className="detail-item">
                    <span>latitude</span>
                    <strong>{hasLocation ? Number(latitude).toFixed(6) : "--"}</strong>
                  </div>
                  <div className="detail-item">
                    <span>longitude</span>
                    <strong>{hasLocation ? Number(longitude).toFixed(6) : "--"}</strong>
                  </div>
                </div>

                <div className="map-wrap">
                  <h3>Battery Location</h3>
                  {hasLocation ? (
                    <iframe
                      className="battery-map"
                      src={mapSrc}
                      title={`Map for ${selectedDeviceId}`}
                      loading="lazy"
                    />
                  ) : (
                    <p className="hint">Location is not available yet for this battery.</p>
                  )}
                </div>

                <div className="cells-wrap">
                  <h3>Cell Voltages Summary</h3>
                  <div className="cells-grid">
                    <div className="cell-chip">
                      <span>Average</span>
                      <strong>{selectedCellStats ? `${selectedCellStats.avg.toFixed(3)} V` : "--"}</strong>
                    </div>
                    <div className="cell-chip">
                      <span>Min</span>
                      <strong>{selectedCellStats ? `${selectedCellStats.min.toFixed(3)} V` : "--"}</strong>
                    </div>
                    <div className="cell-chip">
                      <span>Max</span>
                      <strong>{selectedCellStats ? `${selectedCellStats.max.toFixed(3)} V` : "--"}</strong>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <p className="hint">No battery selected.</p>
            )}
          </section>

          <section className="cards">
            <article className="card">
              <h2>SOC</h2>
              <div className="soc-value">{latest ? `${latest.soc.toFixed(1)}%` : "--"}</div>
              <div className="gauge">
                <div
                  className="gauge-fill"
                  style={{ width: `${latest ? Math.max(0, Math.min(100, latest.soc)) : 0}%` }}
                />
              </div>
            </article>

            <article className="card">
              <h2>Pack Voltage</h2>
              <div className="metric">{latest ? `${latest.pack_voltage.toFixed(2)} V` : "--"}</div>
            </article>

            <article className="card">
              <h2>Temperature</h2>
              <div className="metric">{latest ? `${latest.temperature.toFixed(2)} C` : "--"}</div>
            </article>

            <article className="card">
              <h2>Current</h2>
              <div className="metric">{latest ? `${latest.pack_current.toFixed(2)} A` : "--"}</div>
            </article>

            <article className="card">
              <h2>Cycle Count</h2>
              <div className="metric">{latest ? latest.cycle_count : "--"}</div>
            </article>
          </section>

          <section className="cards">
            <article className="card">
              <h2>Operating Hours</h2>
              <div className="metric">{Number(dailySummary.operating_hours || 0).toFixed(2)} h</div>
            </article>
            <article className="card">
              <h2>Idle Hours</h2>
              <div className="metric">{Number(dailySummary.idle_hours || 0).toFixed(2)} h</div>
            </article>
            <article className="card">
              <h2>Charging Hours</h2>
              <div className="metric">{Number(dailySummary.charging_hours || 0).toFixed(2)} h</div>
            </article>
          </section>

          <section className="cards" aria-label="Battery analytics">
            <article className="card">
              <h2>Average Voltage</h2>
              <div className="metric">
                {analytics ? `${analytics.avg_pack_voltage.toFixed(2)} V` : "--"}
              </div>
            </article>
            <article className="card">
              <h2>Average Current</h2>
              <div className="metric">
                {analytics ? `${analytics.avg_pack_current.toFixed(2)} A` : "--"}
              </div>
            </article>
            <article className="card">
              <h2>Average SOC</h2>
              <div className="metric">
                {analytics ? `${analytics.avg_soc.toFixed(1)}%` : "--"}
              </div>
            </article>
            <article className="card">
              <h2>Average Temperature</h2>
              <div className="metric">
                {analytics ? `${analytics.avg_temperature.toFixed(1)} C` : "--"}
              </div>
            </article>
            <article className="card">
              <h2>Alarm Events</h2>
              <div className="metric">{analytics ? analytics.alarm_events : "--"}</div>
            </article>
            <article className="card">
              <h2>Analytics Samples</h2>
              <div className="metric">{analytics ? analytics.samples : "--"}</div>
            </article>
          </section>

          <section className="charts">
            <TelemetryChart
              title="Voltage"
              labels={chartSeries.labels}
              values={chartSeries.voltage}
              color="#0f4c5c"
              yLabel="Volts"
            />
            <TelemetryChart
              title="Current"
              labels={chartSeries.labels}
              values={chartSeries.current}
              color="#e36414"
              yLabel="Amps"
            />
            <TelemetryChart
              title="Temperature"
              labels={chartSeries.labels}
              values={chartSeries.temperature}
              color="#9a031e"
              yLabel="Celsius"
            />
          </section>

          <section className="table-wrap">
            <h2>Latest Telemetry Records ({selectedDeviceId})</h2>
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Voltage (V)</th>
                  <th>Current (A)</th>
                  <th>SOC (%)</th>
                  <th>Temp (C)</th>
                  <th>Cycle</th>
                  <th>Alarms</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(-10).reverse().map((row) => (
                  <tr key={row.id}>
                    <td>{new Date(row.timestamp).toLocaleTimeString()}</td>
                    <td>{row.pack_voltage.toFixed(2)}</td>
                    <td>{row.pack_current.toFixed(2)}</td>
                    <td>{row.soc.toFixed(1)}</td>
                    <td>{row.temperature.toFixed(2)}</td>
                    <td>{row.cycle_count}</td>
                    <td>{row.alarms.length ? row.alarms.join(", ") : "NONE"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </main>
  );
}

export default Dashboard;
