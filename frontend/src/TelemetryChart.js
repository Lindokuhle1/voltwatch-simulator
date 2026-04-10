import React from "react";
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

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

function TelemetryChart({ title, labels, values, color, yLabel }) {
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
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { display: true, text: title },
    },
    scales: {
      y: {
        title: {
          display: true,
          text: yLabel,
        },
      },
    },
  };

  return (
    <div className="chart-card">
      <Line data={data} options={options} />
    </div>
  );
}

export default TelemetryChart;
