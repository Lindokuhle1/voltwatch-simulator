import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { Chart as ChartJS } from "chart.js";
import TelemetryChart from "./TelemetryChart";

const mockResetZoom = jest.fn();

jest.mock("react-chartjs-2", () => {
  const ReactModule = jest.requireActual("react");
  return {
    Line: ReactModule.forwardRef(({ options }, ref) => {
      ReactModule.useImperativeHandle(ref, () => ({ resetZoom: mockResetZoom }));
      return ReactModule.createElement("div", {
        "data-testid": "line-chart",
        "data-zoom": JSON.stringify(options.plugins.zoom),
      });
    }),
  };
});

beforeEach(() => {
  mockResetZoom.mockClear();
});

test("registers the zoom plugin and reset control resets chart zoom", () => {
  render(
    <TelemetryChart
      title="Voltage and Current"
      labels={["12:00", "12:01"]}
      values={[52, 53]}
      color="#0f4c5c"
      yLabel="Volts"
      additionalSeries={[
        { label: "Current", values: [10, 12], color: "#e36414" },
      ]}
      secondaryYLabel="Amps"
    />
  );

  const zoom = JSON.parse(screen.getByTestId("line-chart").dataset.zoom);
  expect(zoom.zoom.wheel.enabled).toBe(true);
  expect(zoom.zoom.pinch.enabled).toBe(true);
  expect(zoom.zoom.drag.enabled).toBe(true);
  expect(zoom.pan.modifierKey).toBe("shift");
  expect(ChartJS.registry.plugins.get("zoom")).toBeDefined();

  fireEvent.click(screen.getByRole("button", { name: "Reset zoom" }));
  expect(mockResetZoom).toHaveBeenCalledTimes(1);
});
