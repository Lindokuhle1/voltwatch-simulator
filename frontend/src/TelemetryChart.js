import React, { useRef } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";
import zoomPlugin from "chartjs-plugin-zoom";
import "hammerjs";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  zoomPlugin
);

function TelemetryChart({
  title,
  labels,
  values,
  color,
  yLabel,
  additionalSeries = [],
  secondaryYLabel,
  className = "",
}) {
  const chartRef = useRef(null);
  const data = {
    labels,
    datasets: [
      {
        label: title,
        data: values,
        borderColor: color,
        backgroundColor: `${color}33`,
        borderWidth: 2,
        pointRadius: 2,
        tension: 0.25,
        yAxisID: "y",
      },
      ...additionalSeries.map((series) => ({
        label: series.label,
        data: series.values,
        borderColor: series.color,
        backgroundColor: `${series.color}33`,
        borderWidth: 2,
        pointRadius: 2,
        tension: 0.25,
        yAxisID: "y1",
      })),
    ],
  };

  const hasSecondaryAxis = additionalSeries.length > 0;
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: hasSecondaryAxis },
      title: { display: true, text: title },
      zoom: {
        pan: { enabled: true, mode: "x", modifierKey: "shift" },
        zoom: {
          mode: "x",
          wheel: { enabled: true },
          pinch: { enabled: true },
          drag: { enabled: true },
        },
      },
    },
    scales: {
      y: {
        title: {
          display: true,
          text: yLabel,
        },
      },
      ...(hasSecondaryAxis
        ? {
            y1: {
              position: "right",
              grid: { drawOnChartArea: false },
              title: {
                display: true,
                text: secondaryYLabel,
              },
            },
          }
        : {}),
    },
  };

  return (
    <div className={`chart-card ${className}`.trim()}>
      <div className="chart-toolbar">
        <p>Drag across the chart, scroll, or pinch to zoom. Hold Shift and drag to pan.</p>
        <button
          className="nav-btn"
          onClick={() => chartRef.current?.resetZoom()}
          type="button"
        >
          Reset zoom
        </button>
      </div>
      <div className="chart-canvas">
        <Line ref={chartRef} data={data} options={options} />
      </div>
    </div>
  );
}

export default TelemetryChart;
