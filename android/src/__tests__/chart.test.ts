import { EVENT_MARKERS } from "../data/events";
import type { Dataset } from "../types";
import { buildLineChartModel, chartTooltipBounds, compactNumber, formatHoverValue } from "../utils/chart";

const dataset: Dataset = {
  label: "Population",
  borderColor: "#0f766e",
  backgroundColor: "#0f766e",
  data: [
    { x: "1961-12-01", y: 3195.3, label: "1961 Year-end" },
    { x: "1970-12-01", y: 3995.4, label: "1970 Year-end" },
    { x: "1980-12-01", y: 5067.4, label: "1980 Year-end" },
    { x: "1990-12-01", y: 5704.4, label: "1990 Year-end" },
    { x: "2000-12-01", y: 6656.0, label: "2000 Year-end" },
    { x: "2010-12-01", y: 7097.6, label: "2010 Year-end" },
    { x: "2020-12-01", y: 7481.8, label: "2020 Year-end" },
    { x: "2025-12-01", y: 7510.8, label: "2025 Year-end" }
  ]
};

describe("chart utilities", () => {
  it("formats compact values consistently", () => {
    expect(compactNumber(7510.8)).toBe("7.5k");
    expect(compactNumber(12.4)).toBe("12.4");
  });

  it("formats hover values with readable precision", () => {
    expect(formatHoverValue(7510.8)).toBe("7,511");
    expect(formatHoverValue(3.26)).toBe("3.3");
    expect(formatHoverValue(0.345)).toBe("0.35");
  });

  it("builds time ticks and events for the full history", () => {
    const model = buildLineChartModel(dataset, 760, 310, EVENT_MARKERS);
    expect(model.points).toHaveLength(8);
    expect(model.xTicks.some((tick) => tick.label === "1970s")).toBe(true);
    expect(model.xTicks.some((tick) => tick.label === "2000s")).toBe(true);
    expect(model.events.some((event) => event.short === "2003 SARS")).toBe(true);
    expect(model.events.some((event) => event.short === "2020 COVID")).toBe(true);
    expect(model.peakIndex).toBe(7);
  });

  it.each([180, 268, 760])("keeps edge tooltips inside a %ipx chart", (width) => {
    const height = 286;
    for (const x of [0, 52, width - 18, width]) {
      for (const y of [0, 18, height - 40, height]) {
        const bounds = chartTooltipBounds(x, y, width, height);
        expect(bounds.left).toBeGreaterThanOrEqual(10);
        expect(bounds.top).toBeGreaterThanOrEqual(10);
        expect(bounds.left + bounds.boxWidth).toBeLessThanOrEqual(width - 10);
        expect(bounds.top + bounds.boxHeight).toBeLessThanOrEqual(height - 10);
      }
    }
  });

  it("fits the actual narrow viewport while preserving the full event context", () => {
    const width = 238;
    const model = buildLineChartModel(dataset, width, 286, EVENT_MARKERS);
    expect(model.chartRight).toBeLessThan(width);
    expect(model.points[model.peakIndex].x).toBeLessThan(width);
    expect(model.events.map((event) => event.label)).toEqual(EVENT_MARKERS.map((event) => event.label));
    expect(chartTooltipBounds(model.chartRight, model.chartTop, 180, 286).boxWidth).toBe(160);
  });
});
