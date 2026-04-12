export type ReportPoint = {
  x: string;
  y: number;
  label: string;
};

export type Dataset = {
  label: string;
  borderColor: string;
  backgroundColor: string;
  data: ReportPoint[];
};

export type SupportBarItem = {
  label: string;
  value: number;
  display: string;
  color?: string;
};

export type SupportChart = {
  kind: "line" | "bars";
  title: string;
  value: string;
  subtext: string;
  dataset?: Dataset;
  items?: SupportBarItem[];
  color?: string;
};

export type SourceLink = {
  table_id: string;
  title: string;
  last_modified_date: string;
  url: string;
};

export type StatItem = {
  label: string;
  value: string;
};

export type AnalysisSection = {
  id: string;
  title: string;
  headline: string;
  insight: string;
  chart_note: string;
  commentary: string;
  datasets: Dataset[];
  main_dataset_label: string;
  support_charts: SupportChart[];
  stats?: StatItem[];
  sources: SourceLink[];
};

export type ReportPayload = {
  app_title: string;
  generated_at: string;
  latest_release: string;
  sections: AnalysisSection[];
};

export type EventMarker = {
  date: string;
  short: string;
  label: string;
};

export type LineChartPoint = {
  x: number;
  y: number;
  value: number;
  label: string;
  iso: string;
};

export type TickMark = {
  x: number;
  label: string;
};

export type YTick = {
  y: number;
  label: string;
};

export type EventPosition = {
  x: number;
  label: string;
  short: string;
};

export type LineChartModel = {
  points: LineChartPoint[];
  linePath: string;
  areaPath: string;
  xTicks: TickMark[];
  yTicks: YTick[];
  events: EventPosition[];
  peakIndex: number;
  chartLeft: number;
  chartRight: number;
  chartTop: number;
  chartBottom: number;
  width: number;
  height: number;
};
