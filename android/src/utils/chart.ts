import type { Dataset, EventMarker, EventPosition, LineChartModel, TickMark, YTick } from "../types";

export function compactNumber(value: number): string {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}m`;
  }
  if (absolute >= 1_000) {
    return `${(value / 1_000).toFixed(1)}k`;
  }
  return value.toFixed(1);
}

export function formatHoverValue(value: number): string {
  const absolute = Math.abs(value);
  if (absolute >= 1000) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  if (absolute >= 1) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function toTimestamp(iso: string): number {
  return new Date(iso).getTime();
}

function chooseTimeTicks(start: Date, end: Date): TickMark[] {
  const spanYears = Math.max((end.getTime() - start.getTime()) / (365.25 * 24 * 60 * 60 * 1000), 1);
  let step = 1;
  let formatter = (year: number) => `${year}`;
  if (spanYears >= 45) {
    step = 10;
    formatter = (year: number) => `${year}s`;
  } else if (spanYears >= 20) {
    step = 5;
  } else if (spanYears >= 8) {
    step = 2;
  }

  const firstTick = (Math.floor(start.getFullYear() / step) + 1) * step;
  const ticks: TickMark[] = [];
  for (let year = firstTick; year <= end.getFullYear(); year += step) {
    ticks.push({ x: new Date(`${year}-01-01`).getTime(), label: formatter(year) });
  }
  return ticks.slice(0, 8);
}

function chooseYTicks(minValue: number, maxValue: number): number[] {
  const safeMax = maxValue === minValue ? maxValue + 1 : maxValue;
  const ticks = [minValue, minValue + (safeMax - minValue) / 3, minValue + (safeMax - minValue) * 2 / 3, safeMax];
  if (minValue < 0 && safeMax > 0) {
    ticks.push(0);
  }
  return [...new Set(ticks.map((tick) => Number(tick.toFixed(6))))].sort((a, b) => a - b);
}

function xScale(timestamp: number, start: number, end: number, left: number, width: number): number {
  const total = Math.max(end - start, 1);
  return left + ((timestamp - start) / total) * width;
}

function linePath(points: Array<{ x: number; y: number }>): string {
  if (!points.length) {
    return "";
  }
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(" ");
}

export function buildLineChartModel(dataset: Dataset, width: number, height: number, events: EventMarker[]): LineChartModel {
  const chartLeft = 52;
  const chartRight = width - 18;
  const chartTop = 18;
  const chartBottom = height - 40;
  const chartWidth = chartRight - chartLeft;
  const chartHeight = chartBottom - chartTop;
  const points = dataset.data;
  const timestamps = points.map((point) => toTimestamp(point.x));
  const start = timestamps[0];
  const end = timestamps[timestamps.length - 1];
  const values = points.map((point) => point.y);
  const minValue = Math.min(...values);
  const maxValueRaw = Math.max(...values);
  const maxValue = maxValueRaw === minValue ? maxValueRaw + 1 : maxValueRaw;

  const yScale = (value: number) => chartTop + (1 - (value - minValue) / (maxValue - minValue)) * chartHeight;

  const chartPoints = points.map((point, index) => ({
    x: xScale(timestamps[index], start, end, chartLeft, chartWidth),
    y: yScale(point.y),
    value: point.y,
    label: point.label,
    iso: point.x,
  }));

  let peakIndex = 0;
  chartPoints.forEach((point, index) => {
    if (point.value > chartPoints[peakIndex].value) {
      peakIndex = index;
    }
  });

  const xTicks = chooseTimeTicks(new Date(start), new Date(end)).map((tick) => ({
    label: tick.label,
    x: xScale(tick.x, start, end, chartLeft, chartWidth),
  }));
  const yTicks: YTick[] = chooseYTicks(minValue, maxValue).map((value) => ({
    y: yScale(value),
    label: compactNumber(value),
  }));
  const eventPositions: EventPosition[] = events
    .map((event) => ({ ...event, timestamp: toTimestamp(event.date) }))
    .filter((event) => event.timestamp >= start && event.timestamp <= end)
    .map((event) => ({
      x: xScale(event.timestamp, start, end, chartLeft, chartWidth),
      label: event.label,
      short: event.short,
    }));

  const polyPoints = chartPoints.map((point) => ({ x: point.x, y: point.y }));
  const line = linePath(polyPoints);
  const area = polyPoints.length
    ? `${line} L ${polyPoints[polyPoints.length - 1].x.toFixed(2)} ${chartBottom.toFixed(2)} L ${polyPoints[0].x.toFixed(2)} ${chartBottom.toFixed(2)} Z`
    : "";

  return {
    points: chartPoints,
    linePath: line,
    areaPath: area,
    xTicks,
    yTicks,
    events: eventPositions,
    peakIndex,
    chartLeft,
    chartRight,
    chartTop,
    chartBottom,
    width,
    height,
  };
}
