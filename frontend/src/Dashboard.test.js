import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import Dashboard from "./Dashboard";
import {
  getBatteries,
  getBatteryAnalytics,
  getBatteryDailySummary,
  getBatteryStatus,
  getTelemetryHistory,
} from "./api";

jest.mock("./api", () => ({
  downloadMonthlyReport: jest.fn(),
  getBatteries: jest.fn(),
  getBatteryAnalytics: jest.fn(),
  getBatteryDailySummary: jest.fn(),
  getBatteryStatus: jest.fn(),
  getTelemetryHistory: jest.fn(),
}));

jest.mock("./TelemetryChart", () => function MockTelemetryChart(props) {
  return <div data-testid="telemetry-chart">{props.title}</div>;
});

const battery = {
  device_id: "battery_pack_01",
  soc: 84.5,
  alarm_count: 1,
  active: true,
  cell_imbalance: 0.02,
  last_activity: "2026-04-07T12:00:00+00:00",
  pack_voltage: 52.3,
  pack_current: 12.4,
  cycle_count: 4,
  temperature: 33.2,
  latitude: -28.15,
  longitude: 29.53,
  health: "GOOD",
};

beforeEach(() => {
  jest.clearAllMocks();
  getBatteries.mockResolvedValue({ items: [battery] });
  getBatteryStatus.mockResolvedValue({
    health: "GOOD",
    latest: {
      ...battery,
      id: 1,
      timestamp: battery.last_activity,
      cell_voltages: [3.45, ...Array(15).fill(3.46)],
      alarms: [],
    },
  });
  getTelemetryHistory.mockResolvedValue({ items: [] });
  getBatteryDailySummary.mockResolvedValue({
    operating_hours: 1,
    idle_hours: 2,
    charging_hours: 0.5,
    samples: 3,
  });
  getBatteryAnalytics.mockResolvedValue({
    device_id: battery.device_id,
    samples: 25,
    avg_pack_voltage: 52.3,
    avg_pack_current: 12.4,
    avg_soc: 84.5,
    avg_temperature: 33.2,
    alarm_events: 2,
  });
});

test("loads battery list and shows analytics for a selected battery", async () => {
  render(<Dashboard />);

  const batteryRow = await screen.findByText("battery_pack_01");
  expect(getBatteries).toHaveBeenCalledWith(200);
  fireEvent.click(batteryRow);

  expect(await screen.findByText("Average Voltage")).toBeInTheDocument();
  expect(screen.getByText("52.30 V")).toBeInTheDocument();
  expect(screen.getByText("12.40 A")).toBeInTheDocument();
  expect(screen.getByText("84.5%")).toBeInTheDocument();
  expect(screen.getByText("33.20 C")).toBeInTheDocument();
  expect(screen.getByText("Analytics Samples")).toBeInTheDocument();
  const charts = screen.getAllByTestId("telemetry-chart");
  expect(charts).toHaveLength(2);
  expect(within(charts[0]).getByText("Voltage and Current")).toBeInTheDocument();
  const batteryLayout = screen.getByRole("main");
  expect(batteryLayout).toHaveClass("battery-layout");
  expect(batteryLayout.querySelectorAll(":scope > section")[1]).toHaveClass(
    "primary-chart-section"
  );
  expect(getBatteryAnalytics).toHaveBeenCalledWith("battery_pack_01");
});
