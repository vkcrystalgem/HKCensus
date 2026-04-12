from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DIST_DIR = ROOT / "dist"
TEMPLATE_DIR = ROOT / "templates"
MANIFEST_PATH = DATA_DIR / "metadata.json"
MOBILE_EXPORT_SCRIPT = ROOT / "export_mobile_data.py"

BASE_URL = "https://www.censtatd.gov.hk"
USER_AGENT = "Mozilla/5.0 (compatible; HKCensusBot/1.0; +https://www.censtatd.gov.hk/)"
NONBLANK = "__NONBLANK__"


@dataclass(frozen=True)
class SeriesRequest:
    name: str
    table_id: str
    stat_var: str
    stat_pres: str
    filters: dict[str, str] | None = None
    aggregate: str | None = None


SERIES_REQUESTS: list[SeriesRequest] = [
    SeriesRequest("population_total", "110-01001", "POP", "Raw_K_1dp_per_n", {"SEX": "", "AGE": "", "H": "2"}),
    SeriesRequest("population_births", "110-01003", "BIRTHS_PRO", "Raw_K_1dp_per_n", {"H": "2"}),
    SeriesRequest("population_deaths", "110-01003", "DEATHS_PRO", "Raw_K_1dp_per_n", {"H": "2"}),
    SeriesRequest("population_net_movement", "110-01003", "NM", "Raw_K_1dp_per_n", {"H": "2", "TYPE_INFLOW": ""}),
    SeriesRequest("population_growth", "110-01003", "PG", "Raw_K_1dp_per_n", {"H": "2"}),
    SeriesRequest("median_age", "110-01004", "MED_AGE_POPN_XFDH", "Raw_1dp_age_n", {"SEX": ""}),
    SeriesRequest("dependency_ratio", "110-01004", "TDEPR_XFDH", "Ratio_pkpo_n", {"SEX": ""}),
    SeriesRequest("fertility_rate", "115-01011", "TFR_XFDH", "Ratio_pkfpo_n"),
    SeriesRequest("crude_birth_rate", "115-01011", "CBR", "Ratio_1dp_pkpo_n"),
    SeriesRequest("households_total", "130-06601A", "DH_XFDH", "Raw_K_1dp_hh_n", {"Q": "", "HHSIZE": ""}),
    SeriesRequest("households_size_1", "130-06601A", "DH_XFDH", "Raw_K_1dp_hh_n", {"Q": "", "HHSIZE": "1"}),
    SeriesRequest("households_size_2", "130-06601A", "DH_XFDH", "Raw_K_1dp_hh_n", {"Q": "", "HHSIZE": "2"}),
    SeriesRequest("median_household_income", "130-06606A", "MED_DH_INC_XFDH", "Raw_hkd_d", {"Q": "", "HHSIZE": ""}),
    SeriesRequest("labour_force", "210-06101", "LF", "Raw_K_1dp_per_n", {"SEX": "", "M3M": ""}),
    SeriesRequest("labour_force_participation", "210-06101", "LFPR", "Rate_1dp_%_n", {"SEX": "", "M3M": ""}),
    SeriesRequest("seasonally_adjusted_unemployment", "210-06101", "SAUR", "Rate_1dp_%_n", {"SEX": "", "M3M": NONBLANK}),
    SeriesRequest("real_gdp_per_capita", "310-31001", "CONPGDP", "Raw_hkd_d", {"Q": ""}),
    SeriesRequest("real_gdp", "310-31001", "CON", "Raw_M_hkd_d", {"Q": ""}),
    SeriesRequest("cpi_yoy", "510-60001", "CC_CM_1920", "YoY_1dp_%_s", {"MM": NONBLANK}),
]


TABLE_SOURCE_LINKS = {
    "110-01001": "https://www.censtatd.gov.hk/en/web_table.html?id=110-01001",
    "110-01003": "https://www.censtatd.gov.hk/en/web_table.html?id=110-01003",
    "110-01004": "https://www.censtatd.gov.hk/en/web_table.html?id=110-01004",
    "115-01011": "https://www.censtatd.gov.hk/en/web_table.html?id=115-01011",
    "115-01015": "https://www.censtatd.gov.hk/en/web_table.html?id=115-01015",
    "130-06601A": "https://www.censtatd.gov.hk/en/web_table.html?id=130-06601A",
    "130-06606A": "https://www.censtatd.gov.hk/en/web_table.html?id=130-06606A",
    "210-06101": "https://www.censtatd.gov.hk/en/web_table.html?id=210-06101",
    "310-31001": "https://www.censtatd.gov.hk/en/web_table.html?id=310-31001",
    "510-60001": "https://www.censtatd.gov.hk/en/web_table.html?id=510-60001",
}

EVENTS = [
    {"date": "1997-07-01", "short": "1997 Asian crisis", "label": "1997 Asian financial crisis"},
    {"date": "2000-03-10", "short": "2000 tech bubble", "label": "2000 dot-com bubble"},
    {"date": "2003-03-15", "short": "2003 SARS", "label": "2003 SARS outbreak"},
    {"date": "2008-09-15", "short": "2008 GFC", "label": "2008 global financial crisis"},
    {"date": "2020-03-11", "short": "2020 COVID", "label": "2020 COVID-19 shock"},
]


class CenstatdClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.sd_map: dict[str, dict[str, Any]] | None = None

    def get_json(self, url: str) -> dict[str, Any]:
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        return response.json()

    def get_text(self, url: str) -> str:
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        return response.text

    def get_sd_map(self) -> dict[str, dict[str, Any]]:
        if self.sd_map is None:
            self.sd_map = self.get_json(f"{BASE_URL}/data/en/sd_lang.json")
        return self.sd_map


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)


def sanitize_token(token: str) -> str:
    return token.replace("/", "slash").replace("%", "percent").replace("$", "dollar")


def read_manifest() -> dict[str, Any]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"tables": {}}


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def cache_series_csv(
    client: CenstatdClient,
    table_id: str,
    theme_id: str,
    stat_var: str,
    stat_pres: str,
    force_refresh: bool,
) -> Path:
    table_dir = RAW_DIR / table_id
    table_dir.mkdir(exist_ok=True)
    filename = f"MDT_{theme_id}_{table_id}_{sanitize_token(stat_var)}_{sanitize_token(stat_pres)}.csv"
    output_path = table_dir / filename
    if force_refresh or not output_path.exists():
        output_path.write_text(client.get_text(f"{BASE_URL}/data/{filename}"), encoding="utf-8")
    return output_path


def to_float(raw_value: Any, sd_value: Any, sd_map: dict[str, dict[str, Any]]) -> float | None:
    text = "" if pd.isna(raw_value) else str(raw_value).strip()
    sd_code = "" if pd.isna(sd_value) else str(sd_value).strip()
    if not text:
        return None
    if sd_code == "11":
        return 0.0
    if sd_code in {"9", "10", "12"}:
        return None
    info = sd_map.get(sd_code)
    if info and info.get("obs_value_suppressed") == "1":
        return None
    return float(text)


def build_period_frame(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    if "MM" in data.columns and data["MM"].astype(str).str.strip().ne("").any():
        data["month_num"] = data["MM"].astype(str).astype(int)
        data["period_dt"] = pd.to_datetime({"year": data["CCYY"].astype(int), "month": data["month_num"], "day": 1})
        data["period_label"] = data["period_dt"].dt.strftime("%Y-%m")
        return data
    if "Q" in data.columns and data["Q"].astype(str).str.strip().ne("").any():
        data["quarter_num"] = data["Q"].astype(str).astype(int)
        data["period_dt"] = pd.to_datetime({"year": data["CCYY"].astype(int), "month": data["quarter_num"] * 3, "day": 1})
        data["period_label"] = data["CCYY"].astype(str) + "-Q" + data["quarter_num"].astype(str)
        return data
    if "M3M" in data.columns and data["M3M"].astype(str).str.strip().ne("").any():
        data["m3m_num"] = data["M3M"].astype(str).astype(int)
        data["period_dt"] = pd.to_datetime({"year": data["CCYY"].astype(int), "month": data["m3m_num"], "day": 1})
        data["period_label"] = data["period_dt"].dt.strftime("%Y-%m")
        return data
    if "H" in data.columns and data["H"].astype(str).str.strip().ne("").any():
        month = data["H"].astype(str).map({"1": 6, "2": 12}).fillna("12").astype(int)
        label = data["H"].astype(str).map({"1": "Mid-year", "2": "Year-end"}).fillna("Reference")
        data["period_dt"] = pd.to_datetime({"year": data["CCYY"].astype(int), "month": month, "day": 1})
        data["period_label"] = data["CCYY"].astype(str) + " " + label
        return data
    data["period_dt"] = pd.to_datetime({"year": data["CCYY"].astype(int), "month": 1, "day": 1})
    data["period_label"] = data["CCYY"].astype(str)
    return data


def extract_series(
    client: CenstatdClient,
    request: SeriesRequest,
    table_meta: dict[str, tuple[dict[str, Any], dict[str, Any]]],
    force_refresh: bool,
) -> pd.DataFrame:
    comp, _lang = table_meta[request.table_id]
    csv_path = cache_series_csv(client, request.table_id, str(comp["theme_id"]), request.stat_var, request.stat_pres, force_refresh)
    frame = pd.read_csv(csv_path, dtype=str).fillna("")
    for column, expected in (request.filters or {}).items():
        if column not in frame.columns:
            continue
        values = frame[column].astype(str).str.strip()
        frame = frame[values.ne("")] if expected == NONBLANK else frame[values.eq(expected)]
    frame["value"] = [to_float(obs, sd, client.get_sd_map()) for obs, sd in zip(frame["obs_value"], frame["sd_value"], strict=True)]
    frame = frame.dropna(subset=["value"]).copy()
    if request.aggregate == "sum":
        time_columns = [column for column in ["CCYY", "Q", "MM", "M3M", "H"] if column in frame.columns]
        frame["value"] = frame["value"].astype(float)
        frame = frame.groupby(time_columns, dropna=False, as_index=False)["value"].sum()
    frame = build_period_frame(frame)
    frame["value"] = frame["value"].astype(float)
    frame = frame.sort_values("period_dt").reset_index(drop=True)
    frame["period_iso"] = frame["period_dt"].dt.strftime("%Y-%m-%d")
    return frame[["period_label", "period_iso", "period_dt", "value"]]


def latest_value(series: pd.DataFrame) -> float:
    return float(series.iloc[-1]["value"])


def first_value(series: pd.DataFrame) -> float:
    return float(series.iloc[0]["value"])


def peak_point(series: pd.DataFrame) -> tuple[str, float]:
    row = series.loc[series["value"].idxmax()]
    return str(row["period_label"]), float(row["value"])


def trough_point(series: pd.DataFrame) -> tuple[str, float]:
    row = series.loc[series["value"].idxmin()]
    return str(row["period_label"]), float(row["value"])


def fmt_number(value: float, decimals: int = 1, suffix: str = "") -> str:
    return f"{value:,.{decimals}f}{suffix}"


def fmt_change(start: float, end: float, decimals: int = 1) -> str:
    if start == 0:
        return "n/a"
    return f"{((end / start) - 1) * 100:,.{decimals}f}%"


def series_payload(label: str, frame: pd.DataFrame, color: str) -> dict[str, Any]:
    return {
        "label": label,
        "borderColor": color,
        "backgroundColor": color,
        "data": [{"x": row["period_iso"], "y": round(float(row["value"]), 4), "label": row["period_label"]} for _, row in frame.iterrows()],
    }


def frame_to_dataset(label: str, frame: pd.DataFrame, color: str) -> dict[str, Any]:
    return series_payload(label, frame[["period_label", "period_iso", "value"]], color)


def derived_share_frame(numerator: pd.DataFrame, denominator: pd.DataFrame) -> pd.DataFrame:
    left = numerator[["period_label", "period_iso", "period_dt", "value"]].rename(columns={"value": "num"})
    right = denominator[["period_iso", "value"]].rename(columns={"value": "den"})
    merged = left.merge(right, on="period_iso", how="inner")
    merged["value"] = (merged["num"] / merged["den"]) * 100
    return merged[["period_label", "period_iso", "period_dt", "value"]]


def derived_difference_frame(minuend: pd.DataFrame, subtrahend: pd.DataFrame) -> pd.DataFrame:
    left = minuend[["period_label", "period_iso", "period_dt", "value"]].rename(columns={"value": "a"})
    right = subtrahend[["period_iso", "value"]].rename(columns={"value": "b"})
    merged = left.merge(right, on="period_iso", how="inner")
    merged["value"] = merged["a"] - merged["b"]
    return merged[["period_label", "period_iso", "period_dt", "value"]]


def derived_pct_change_frame(frame: pd.DataFrame) -> pd.DataFrame:
    changed = frame[["period_label", "period_iso", "period_dt", "value"]].copy()
    changed["value"] = changed["value"].pct_change() * 100
    changed = changed.dropna().reset_index(drop=True)
    return changed


def compact_number(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:.1f}"


def latest_change(dataset: dict[str, Any]) -> str:
    points = dataset["data"]
    start = float(points[0]["y"])
    end = float(points[-1]["y"])
    return fmt_change(start, end)


def peak_dataset_point(dataset: dict[str, Any]) -> dict[str, Any]:
    return max(dataset["data"], key=lambda item: float(item["y"]))


def trough_dataset_point(dataset: dict[str, Any]) -> dict[str, Any]:
    return min(dataset["data"], key=lambda item: float(item["y"]))


def point_timestamp(point: dict[str, Any]) -> pd.Timestamp:
    return pd.Timestamp(point["x"])


def x_scale(ts: pd.Timestamp, start_ts: pd.Timestamp, end_ts: pd.Timestamp, left: int, width: int) -> float:
    total = max((end_ts - start_ts).total_seconds(), 1.0)
    ratio = (ts - start_ts).total_seconds() / total
    return left + ratio * width


def choose_time_ticks(start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> list[tuple[pd.Timestamp, str]]:
    span_years = max((end_ts - start_ts).days / 365.25, 1)
    if span_years >= 45:
        step = 10
        formatter = lambda year: f"{year}s"
    elif span_years >= 20:
        step = 5
        formatter = lambda year: str(year)
    elif span_years >= 8:
        step = 2
        formatter = lambda year: str(year)
    else:
        step = 1
        formatter = lambda year: str(year)

    first_tick = ((start_ts.year // step) + 1) * step
    ticks: list[tuple[pd.Timestamp, str]] = []
    for year in range(first_tick, end_ts.year + 1, step):
        tick_ts = pd.Timestamp(f"{year}-01-01")
        if start_ts <= tick_ts <= end_ts:
            ticks.append((tick_ts, formatter(year)))
    return ticks[:8]


def choose_y_ticks(min_y: float, max_y: float) -> list[float]:
    if max_y == min_y:
        max_y = min_y + 1.0
    ticks = [min_y, min_y + (max_y - min_y) / 3, min_y + 2 * (max_y - min_y) / 3, max_y]
    if min_y < 0 < max_y:
        ticks.append(0.0)
    deduped = sorted({round(tick, 6) for tick in ticks})
    return deduped


def visible_events(start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> list[dict[str, str]]:
    return [event for event in EVENTS if start_ts <= pd.Timestamp(event["date"]) <= end_ts]


def nearest_point(dataset: dict[str, Any], when: pd.Timestamp) -> dict[str, Any]:
    return min(dataset["data"], key=lambda point: abs(point_timestamp(point) - when))


def decade_change_items(dataset: dict[str, Any], percent: bool = False, max_items: int = 5) -> list[dict[str, Any]]:
    points = dataset["data"]
    start_ts = point_timestamp(points[0])
    end_ts = point_timestamp(points[-1])
    step = 10
    labels: list[dict[str, Any]] = []
    year = ((start_ts.year // step) + 1) * step
    while year <= end_ts.year:
        anchor = pd.Timestamp(f"{year}-01-01")
        end_point = nearest_point(dataset, anchor)
        previous_anchor = pd.Timestamp(f"{year - step}-01-01")
        start_point = nearest_point(dataset, previous_anchor)
        start_value = float(start_point["y"])
        end_value = float(end_point["y"])
        value = ((end_value / start_value) - 1) * 100 if percent and start_value != 0 else end_value - start_value
        labels.append(
            {
                "label": f"{year-step}s",
                "value": value,
                "display": f"{value:+.1f}%" if percent else compact_number(value),
            }
        )
        year += step
    if not labels:
        return []
    return labels[-max_items:]


def latest_snapshot_items(datasets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for dataset in datasets:
        latest = dataset["data"][-1]
        items.append({"label": dataset["label"][:14], "value": float(latest["y"]), "display": compact_number(float(latest["y"]))})
    return items


def event_snapshot_items(dataset: dict[str, Any], include_latest: bool = True) -> list[dict[str, Any]]:
    points = []
    start_ts = point_timestamp(dataset["data"][0])
    end_ts = point_timestamp(dataset["data"][-1])
    for event in visible_events(start_ts, end_ts):
        nearest = nearest_point(dataset, pd.Timestamp(event["date"]))
        points.append({"label": event["short"].replace(" crisis", "").replace(" bubble", ""), "value": float(nearest["y"]), "display": compact_number(float(nearest["y"]))})
    if include_latest:
        latest = dataset["data"][-1]
        points.append({"label": "Latest", "value": float(latest["y"]), "display": compact_number(float(latest["y"]))})
    return points[-5:]


def recent_dataset(dataset: dict[str, Any], count: int) -> dict[str, Any]:
    return {**dataset, "data": dataset["data"][-count:]}


def comparison_items(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    start = dataset["data"][0]
    latest = dataset["data"][-1]
    peak = peak_dataset_point(dataset)
    return [
        {"label": "Start", "value": float(start["y"]), "display": compact_number(float(start["y"]))},
        {"label": "Latest", "value": float(latest["y"]), "display": compact_number(float(latest["y"]))},
        {"label": "Peak", "value": float(peak["y"]), "display": compact_number(float(peak["y"]))},
    ]


def format_hover_value(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1000:
        return f"{value:,.0f}"
    if abs_value >= 1:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def hover_chip_position(x: float, y: float, width: int, height: int, box_w: float, box_h: float) -> tuple[float, float]:
    preferred_x = x + 10
    if preferred_x + box_w > width - 10:
        preferred_x = x - box_w - 10
    chip_x = max(10.0, preferred_x)

    preferred_y = y - box_h - 10
    if preferred_y < 10:
        preferred_y = y + 10
    chip_y = min(max(10.0, preferred_y), height - box_h - 10)
    return chip_x, chip_y


def svg_hover_markup(
    dataset: dict[str, Any],
    xs: list[float],
    y_values: list[float],
    chart_left: int,
    chart_top: int,
    chart_right: int,
    chart_bottom: int,
    width: int,
    height: int,
) -> str:
    points = dataset["data"]
    groups: list[str] = []
    for index, point in enumerate(points):
        x = xs[index]
        y = y_values[index]
        prev_x = chart_left if index == 0 else (xs[index - 1] + x) / 2
        next_x = chart_right if index == len(points) - 1 else (x + xs[index + 1]) / 2
        zone_w = max(next_x - prev_x, 1)
        label_text = f"{point['label']} | {format_hover_value(float(point['y']))}"
        box_w = min(248.0, 22.0 + len(label_text) * 5.8)
        box_h = 28.0
        chip_x, chip_y = hover_chip_position(x, y, width, height, box_w, box_h)
        groups.append(
            f'''
  <g class="hover-zone">
    <rect class="hover-hit" x="{prev_x:.2f}" y="{chart_top}" width="{zone_w:.2f}" height="{chart_bottom-chart_top}" fill="#ffffff" fill-opacity="0"/>
    <line class="hover-line" x1="{x:.2f}" y1="{chart_top}" x2="{x:.2f}" y2="{chart_bottom}" stroke="{dataset["borderColor"]}" stroke-opacity="0.55" stroke-width="1.4" stroke-dasharray="4 4"/>
    <circle class="hover-dot" cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{dataset["borderColor"]}" stroke="#fffaf1" stroke-width="2"/>
    <g class="hover-chip" transform="translate({chip_x:.2f},{chip_y:.2f})">
      <rect width="{box_w:.2f}" height="{box_h:.2f}" rx="10" fill="rgba(255,250,241,0.98)" stroke="rgba(98,95,87,0.24)"/>
      <text x="10" y="18" font-size="11" fill="#1d1d1b">{html.escape(label_text)}</text>
    </g>
  </g>'''.strip()
        )
    return "".join(groups)


def svg_line_chart(dataset: dict[str, Any], width: int = 760, height: int = 310, fill: bool = True) -> str:
    points = dataset["data"]
    color = dataset["borderColor"]
    timestamps = [point_timestamp(point) for point in points]
    start_ts = timestamps[0]
    end_ts = timestamps[-1]
    padding_left = 58
    padding_right = 20
    padding_top = 22
    padding_bottom = 52
    inner_w = width - padding_left - padding_right
    inner_h = height - padding_top - padding_bottom
    ys = [float(point["y"]) for point in points]
    min_y = min(ys)
    max_y = max(ys)
    if max_y == min_y:
        max_y = min_y + 1.0

    def y_at(value: float) -> float:
        return padding_top + (1 - ((value - min_y) / (max_y - min_y))) * inner_h

    def x_at(point: dict[str, Any]) -> float:
        return x_scale(point_timestamp(point), start_ts, end_ts, padding_left, inner_w)

    xs = [x_at(point) for point in points]
    point_ys = [y_at(float(point["y"])) for point in points]
    path_points = [f"{x:.2f},{y:.2f}" for x, y in zip(xs, point_ys, strict=True)]
    line_path = " ".join(path_points)
    area_path = f"M {path_points[0]} L {line_path} L {x_at(points[-1]):.2f},{padding_top + inner_h:.2f} L {x_at(points[0]):.2f},{padding_top + inner_h:.2f} Z"
    peak = peak_dataset_point(dataset)
    peak_x = x_at(peak)
    peak_y = y_at(float(peak["y"]))
    hover_markup = svg_hover_markup(
        dataset=dataset,
        xs=xs,
        y_values=point_ys,
        chart_left=padding_left,
        chart_top=padding_top,
        chart_right=width - padding_right,
        chart_bottom=padding_top + inner_h,
        width=width,
        height=height,
    )

    y_tick_markup = []
    for tick in choose_y_ticks(min_y, max_y):
        y = y_at(float(tick))
        y_tick_markup.append(
            f'<line x1="{padding_left}" y1="{y:.2f}" x2="{width-padding_right}" y2="{y:.2f}" stroke="rgba(98,95,87,0.14)" stroke-width="1"/>'
            f'<text x="{padding_left-8}" y="{y+4:.2f}" text-anchor="end" font-size="11" fill="#625f57">{html.escape(compact_number(float(tick)))}</text>'
        )

    x_tick_markup = []
    for tick_ts, label in choose_time_ticks(start_ts, end_ts):
        x = x_scale(tick_ts, start_ts, end_ts, padding_left, inner_w)
        x_tick_markup.append(
            f'<line x1="{x:.2f}" y1="{padding_top+inner_h:.2f}" x2="{x:.2f}" y2="{padding_top+inner_h+6:.2f}" stroke="rgba(98,95,87,0.22)" stroke-width="1"/>'
            f'<text x="{x:.2f}" y="{height-18}" text-anchor="middle" font-size="11" fill="#625f57">{html.escape(label)}</text>'
        )

    event_markup = []
    for index, event in enumerate(visible_events(start_ts, end_ts)):
        event_ts = pd.Timestamp(event["date"])
        x = x_scale(event_ts, start_ts, end_ts, padding_left, inner_w)
        y_text = padding_top + 14 + (index % 2) * 14
        event_markup.append(
            f'<line x1="{x:.2f}" y1="{padding_top:.2f}" x2="{x:.2f}" y2="{padding_top+inner_h:.2f}" stroke="#7f1d1d" stroke-opacity="0.35" stroke-width="1.2" stroke-dasharray="5 4"/>'
            f'<text x="{x+5:.2f}" y="{y_text:.2f}" font-size="10" fill="#7f1d1d">{html.escape(event["short"])}</text>'
        )

    return f"""
<svg viewBox="0 0 {width} {height}" class="main-svg" role="img" aria-label="{html.escape(dataset['label'])}">
  <rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="#fffaf1"/>
  {''.join(y_tick_markup)}
  {''.join(event_markup)}
  {'<path d="' + area_path + '" fill="' + color + '" opacity="0.10"/>' if fill else ''}
  <polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{line_path}"/>
  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="4.5" fill="{color}"/>
  <text x="{peak_x:.2f}" y="{peak_y-11:.2f}" text-anchor="middle" font-size="11" fill="#1d1d1b">Peak {html.escape(compact_number(float(peak['y'])))}</text>
  <g class="hover-layer">
    {hover_markup}
  </g>
  {''.join(x_tick_markup)}
  <text x="{padding_left}" y="18" font-size="13" font-weight="700" fill="{color}">{html.escape(dataset['label'])}</text>
</svg>
""".strip()


def svg_sparkline(dataset: dict[str, Any], width: int = 240, height: int = 80) -> str:
    points = dataset["data"]
    color = dataset["borderColor"]
    pad = 8
    ys = [float(point["y"]) for point in points]
    min_y = min(ys)
    max_y = max(ys)
    if max_y == min_y:
        max_y = min_y + 1.0

    def x_at(index: int) -> float:
        if len(points) == 1:
            return width / 2
        return pad + (index / (len(points) - 1)) * (width - 2 * pad)

    def y_at(value: float) -> float:
        return pad + (1 - ((value - min_y) / (max_y - min_y))) * (height - 2 * pad)

    polyline = " ".join(f"{x_at(i):.2f},{y_at(float(p['y'])):.2f}" for i, p in enumerate(points))
    return f"""
<svg viewBox="0 0 {width} {height}" class="mini-svg" role="img" aria-label="{html.escape(dataset['label'])}">
  <rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="#fff"/>
  <polyline fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" points="{polyline}"/>
  <circle cx="{x_at(len(points)-1):.2f}" cy="{y_at(float(points[-1]['y'])):.2f}" r="3.5" fill="{color}"/>
</svg>
""".strip()


def svg_bar_chart(items: list[dict[str, Any]], width: int = 240, height: int = 126, color: str = "#0f766e") -> str:
    if not items:
        return ""
    left = 20
    right = 18
    top = 18
    bottom = 34
    inner_w = width - left - right
    inner_h = height - top - bottom
    values = [float(item["value"]) for item in items]
    min_v = min(0.0, min(values))
    max_v = max(0.0, max(values))
    if min_v == max_v:
        max_v = min_v + 1.0

    def y_at(value: float) -> float:
        return top + (1 - ((value - min_v) / (max_v - min_v))) * inner_h

    baseline = y_at(0.0)
    gap = 10
    bar_w = min(42, (inner_w - gap * (len(items) - 1)) / max(len(items), 1))
    total_w = len(items) * bar_w + (len(items) - 1) * gap
    start_x = left + (inner_w - total_w) / 2
    bars = [f'<line x1="{left}" y1="{baseline:.2f}" x2="{width-right}" y2="{baseline:.2f}" stroke="rgba(98,95,87,0.16)" stroke-width="1"/>']
    for index, item in enumerate(items):
        value = float(item["value"])
        x = start_x + index * (bar_w + gap)
        y = min(y_at(value), baseline)
        h = max(abs(y_at(value) - baseline), 1.5)
        fill = item.get("color", color)
        label_y = y - 6 if value >= 0 else y + h + 13
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" rx="8" fill="{fill}" opacity="0.80"/>'
            f'<text x="{x + bar_w/2:.2f}" y="{label_y:.2f}" text-anchor="middle" font-size="10" fill="#1d1d1b">{html.escape(str(item.get("display", compact_number(value))))}</text>'
            f'<text x="{x + bar_w/2:.2f}" y="{height-10}" text-anchor="middle" font-size="10" fill="#625f57">{html.escape(str(item["label"]))}</text>'
        )
    return f"""
<svg viewBox="0 0 {width} {height}" class="mini-svg" role="img" aria-label="bar chart">
  <rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="#fff"/>
  {''.join(bars)}
</svg>
""".strip()


def render_support_chart(spec: dict[str, Any]) -> dict[str, Any]:
    kind = spec["kind"]
    svg = ""
    if kind == "line":
        svg = svg_sparkline(spec["dataset"])
    elif kind == "bars":
        svg = svg_bar_chart(spec["items"], color=spec.get("color", "#0f766e"))
    return {
        "title": spec["title"],
        "value": spec["value"],
        "subtext": spec["subtext"],
        "svg": svg,
    }


def decorate_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    main_dataset = analysis.get("main_dataset") or analysis["datasets"][0]
    stats = [
        {"label": "Coverage", "value": f"{main_dataset['data'][0]['label']} to {main_dataset['data'][-1]['label']}"},
        {"label": "Latest", "value": compact_number(float(main_dataset["data"][-1]["y"]))},
        {"label": "Change", "value": latest_change(main_dataset)},
        {"label": "Peak", "value": f"{compact_number(float(peak_dataset_point(main_dataset)['y']))} | {peak_dataset_point(main_dataset)['label']}"},
    ]
    supplements = [render_support_chart(spec) for spec in analysis.get("support_charts", [])]
    analysis["main_chart_svg"] = svg_line_chart(main_dataset)
    analysis["stats"] = stats
    analysis["supplements"] = supplements
    analysis["main_series_label"] = main_dataset["label"]
    return analysis


def build_sources(table_ids: list[str], table_meta: dict[str, tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for table_id in table_ids:
        if table_id in seen:
            continue
        seen.add(table_id)
        comp, lang = table_meta[table_id]
        sources.append(
            {
                "table_id": table_id,
                "title": lang["tb_title"],
                "last_modified_date": comp["last_modified_date"],
                "url": TABLE_SOURCE_LINKS[table_id],
            }
        )
    return sources


def build_analyses(series_map: dict[str, pd.DataFrame], table_meta: dict[str, tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
    colors = {
        "teal": "#0f766e",
        "orange": "#c2410c",
        "gold": "#a16207",
        "blue": "#1d4ed8",
        "red": "#b91c1c",
        "slate": "#334155",
        "green": "#15803d",
        "indigo": "#4338ca",
        "rose": "#be123c",
        "brown": "#7c2d12",
    }

    analyses: list[dict[str, Any]] = []

    population_total = series_map["population_total"]
    pop_peak_label, pop_peak = peak_point(population_total)
    population_dataset = frame_to_dataset("Population", population_total, colors["teal"])
    analyses.append(
        {
            "id": "population-level",
            "title": "Population level",
            "headline": f"{population_total.iloc[-1]['period_label']}: {fmt_number(latest_value(population_total), 1)} thousand",
            "insight": (
                f"Year-end population moved from {fmt_number(first_value(population_total), 1)} thousand in {population_total.iloc[0]['period_label']} "
                f"to {fmt_number(latest_value(population_total), 1)} thousand in {population_total.iloc[-1]['period_label']}. "
                f"The historical peak was {fmt_number(pop_peak, 1)} thousand in {pop_peak_label}."
            ),
            "chart_note": "Year-end population, both sexes, all ages. Event lines mark major external shocks where they fall within the time range.",
            "datasets": [population_dataset],
            "main_dataset": population_dataset,
            "support_charts": [
                {
                    "kind": "bars",
                    "title": "Decade change",
                    "value": "Population delta by decade",
                    "subtext": "Absolute change versus the prior decade anchor.",
                    "items": decade_change_items(population_dataset),
                    "color": colors["teal"],
                },
                {
                    "kind": "line",
                    "title": "Recent slope",
                    "value": recent_dataset(population_dataset, 14)["data"][-1]["label"],
                    "subtext": "The last 14 annual observations, isolated from the long history.",
                    "dataset": recent_dataset(population_dataset, 14),
                },
            ],
            "commentary": "The long history still trends upward, but the late-series slope is flatter than in the earlier expansion decades.",
            "sources": build_sources(["110-01001"], table_meta),
        }
    )

    births = series_map["population_births"]
    deaths = series_map["population_deaths"]
    net_movement = series_map["population_net_movement"]
    growth = series_map["population_growth"]
    growth_peak_label, growth_peak = peak_point(growth)
    births_dataset = frame_to_dataset("Births", births, colors["blue"])
    deaths_dataset = frame_to_dataset("Deaths", deaths, colors["red"])
    net_movement_dataset = frame_to_dataset("Net movement", net_movement, colors["orange"])
    growth_dataset = frame_to_dataset("Population growth", growth, colors["slate"])
    natural_change_dataset = frame_to_dataset("Natural increase", derived_difference_frame(births, deaths), colors["green"])
    analyses.append(
        {
            "id": "population-growth-components",
            "title": "Population growth components",
            "headline": f"{growth.iloc[-1]['period_label']}: growth {fmt_number(latest_value(growth), 1)} thousand, net movement {fmt_number(latest_value(net_movement), 1)} thousand",
            "insight": (
                f"Population growth peaked at {fmt_number(growth_peak, 1)} thousand in {growth_peak_label}. "
                f"In the latest year, births were {fmt_number(latest_value(births), 1)} thousand and deaths were {fmt_number(latest_value(deaths), 1)} thousand."
            ),
            "chart_note": "Annual year-end population growth history. Event lines provide timing context for shocks and recoveries.",
            "datasets": [
                growth_dataset,
                births_dataset,
                deaths_dataset,
                net_movement_dataset,
                natural_change_dataset,
            ],
            "main_dataset": growth_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Natural increase",
                    "value": compact_number(float(natural_change_dataset["data"][-1]["y"])),
                    "subtext": "Births minus deaths across the full series.",
                    "dataset": natural_change_dataset,
                },
                {
                    "kind": "bars",
                    "title": "Latest drivers",
                    "value": growth_dataset["data"][-1]["label"],
                    "subtext": "Latest year comparison across the main growth drivers.",
                    "items": latest_snapshot_items([births_dataset, deaths_dataset, net_movement_dataset, growth_dataset]),
                    "color": colors["slate"],
                },
            ],
            "commentary": "Natural increase has weakened over time, so swings in net movement now have a much larger influence on the headline growth result.",
            "sources": build_sources(["110-01003"], table_meta),
        }
    )

    median_age = series_map["median_age"]
    dependency_ratio = series_map["dependency_ratio"]
    median_age_dataset = frame_to_dataset("Median age", median_age, colors["gold"])
    dependency_ratio_dataset = frame_to_dataset("Dependency ratio", dependency_ratio, colors["indigo"])
    analyses.append(
        {
            "id": "ageing",
            "title": "Ageing and dependency",
            "headline": f"{median_age.iloc[-1]['period_label']}: median age {fmt_number(latest_value(median_age), 1)}, dependency ratio {fmt_number(latest_value(dependency_ratio), 1)}",
            "insight": (
                f"Median age rose by {fmt_number(latest_value(median_age) - first_value(median_age), 1)} years over the series, "
                f"while the total dependency ratio increased from {fmt_number(first_value(dependency_ratio), 1)} to {fmt_number(latest_value(dependency_ratio), 1)}."
            ),
            "chart_note": "Annual population ageing indicators, excluding foreign domestic helpers. Event lines matter less here because the shift is structural rather than cyclical.",
            "datasets": [median_age_dataset, dependency_ratio_dataset],
            "main_dataset": median_age_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Dependency ratio",
                    "value": compact_number(float(dependency_ratio_dataset["data"][-1]["y"])),
                    "subtext": "How many dependants are supported per 1,000 working-age people.",
                    "dataset": dependency_ratio_dataset,
                },
                {
                    "kind": "bars",
                    "title": "Median age milestones",
                    "value": latest_change(median_age_dataset),
                    "subtext": "Start, latest and peak age markers from the full history.",
                    "items": comparison_items(median_age_dataset),
                    "color": colors["gold"],
                },
            ],
            "commentary": "The ageing story is persistent across shocks: short crises interrupt economic series, but they do not reverse the demographic direction of travel.",
            "sources": build_sources(["110-01004"], table_meta),
        }
    )

    fertility = series_map["fertility_rate"]
    crude_birth_rate = series_map["crude_birth_rate"]
    fertility_peak_label, fertility_peak = peak_point(fertility)
    fertility_dataset = frame_to_dataset("Total fertility rate", fertility, colors["rose"])
    crude_birth_dataset = frame_to_dataset("Crude birth rate", crude_birth_rate, colors["orange"])
    analyses.append(
        {
            "id": "fertility",
            "title": "Fertility pressure",
            "headline": f"{fertility.iloc[-1]['period_label']}: TFR {fmt_number(latest_value(fertility), 2)}, crude birth rate {fmt_number(latest_value(crude_birth_rate), 1)} per 1,000",
            "insight": (
                f"Total fertility fell from a peak of {fmt_number(fertility_peak, 2)} in {fertility_peak_label} "
                f"to {fmt_number(latest_value(fertility), 2)} in the latest release."
            ),
            "chart_note": "Annual fertility indicators. Event lines are included for orientation, but the dominant pattern is the long-run downtrend.",
            "datasets": [fertility_dataset, crude_birth_dataset],
            "main_dataset": fertility_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Crude birth rate",
                    "value": compact_number(float(crude_birth_dataset["data"][-1]["y"])),
                    "subtext": "Births per 1,000 population across the same history.",
                    "dataset": crude_birth_dataset,
                },
                {
                    "kind": "bars",
                    "title": "Fertility milestones",
                    "value": latest_change(fertility_dataset),
                    "subtext": "Start, latest and historical peak in the total fertility rate.",
                    "items": comparison_items(fertility_dataset),
                    "color": colors["rose"],
                },
            ],
            "commentary": "The fertility decline is much larger than any temporary rebound, which is why the ageing and household sections reinforce this one.",
            "sources": build_sources(["115-01011"], table_meta),
        }
    )

    households_total = series_map["households_total"]
    one_two_share = derived_share_frame(series_map["households_size_1"], households_total)
    two_person_share = derived_share_frame(series_map["households_size_2"], households_total)
    one_two_share["value"] = one_two_share["value"] + two_person_share["value"].reset_index(drop=True)
    one_two_dataset = frame_to_dataset("1-2 person household share", one_two_share, colors["slate"])
    one_person_dataset = frame_to_dataset("1 person household share", derived_share_frame(series_map["households_size_1"], households_total), colors["orange"])
    two_person_dataset = frame_to_dataset("2 person household share", two_person_share, colors["teal"])
    analyses.append(
        {
            "id": "household-structure",
            "title": "Household downsizing",
            "headline": f"{one_two_share.iloc[-1]['period_label']}: 1-2 person households = {fmt_number(latest_value(one_two_share), 1)}% of all households",
            "insight": (
                f"The one-to-two-person share rose from {fmt_number(first_value(one_two_share), 1)}% to "
                f"{fmt_number(latest_value(one_two_share), 1)}% across the series."
            ),
            "chart_note": "Annual share computed from Domestic households by household size (excluding foreign domestic helpers).",
            "datasets": [one_two_dataset, one_person_dataset, two_person_dataset],
            "main_dataset": one_two_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "One-person households",
                    "value": compact_number(float(one_person_dataset["data"][-1]["y"])),
                    "subtext": "Share of all domestic households occupied by one person.",
                    "dataset": one_person_dataset,
                },
                {
                    "kind": "line",
                    "title": "Two-person households",
                    "value": compact_number(float(two_person_dataset["data"][-1]["y"])),
                    "subtext": "Share of all domestic households occupied by two people.",
                    "dataset": two_person_dataset,
                },
            ],
            "commentary": "Housing demand can keep rising even when headline population slows, because smaller household size increases the number of households that need space.",
            "sources": build_sources(["130-06601A"], table_meta),
        }
    )

    income = series_map["median_household_income"]
    income_dataset = frame_to_dataset("Median monthly household income", income, colors["green"])
    income_growth_dataset = frame_to_dataset("Income YoY change", derived_pct_change_frame(income), colors["gold"])
    analyses.append(
        {
            "id": "household-income",
            "title": "Household income",
            "headline": f"{income.iloc[-1]['period_label']}: HK${fmt_number(latest_value(income), 0)} median monthly income",
            "insight": (
                f"Median monthly household income rose from HK${fmt_number(first_value(income), 0)} to "
                f"HK${fmt_number(latest_value(income), 0)}, a nominal increase of {fmt_change(first_value(income), latest_value(income))}."
            ),
            "chart_note": "Annual overall median, excluding foreign domestic helpers. This section uses the income level as the main history and the year-on-year rate as a supporting read.",
            "datasets": [income_dataset, income_growth_dataset],
            "main_dataset": income_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Income growth rate",
                    "value": f"{float(income_growth_dataset['data'][-1]['y']):+.1f}%",
                    "subtext": "Year-on-year change in the annual median household income series.",
                    "dataset": income_growth_dataset,
                },
                {
                    "kind": "bars",
                    "title": "Income milestones",
                    "value": latest_change(income_dataset),
                    "subtext": "Start, latest and peak income levels in nominal HK dollars.",
                    "items": comparison_items(income_dataset),
                    "color": colors["green"],
                },
            ],
            "commentary": "The long-run rise is clear, but this is a nominal series, so it should be read alongside the inflation section rather than on its own.",
            "sources": build_sources(["130-06606A"], table_meta),
        }
    )

    labour_force = series_map["labour_force"]
    lfpr = series_map["labour_force_participation"]
    lfpr_peak_label, lfpr_peak = peak_point(lfpr)
    lfpr_dataset = frame_to_dataset("Labour force participation rate", lfpr, colors["blue"])
    labour_force_dataset = frame_to_dataset("Labour force", labour_force, colors["teal"])
    analyses.append(
        {
            "id": "labour-force",
            "title": "Labour force participation",
            "headline": f"{lfpr.iloc[-1]['period_label']}: participation {fmt_number(latest_value(lfpr), 1)}%, labour force {fmt_number(latest_value(labour_force), 1)} thousand",
            "insight": (
                f"Participation peaked at {fmt_number(lfpr_peak, 1)}% in {lfpr_peak_label} and now sits at "
                f"{fmt_number(latest_value(lfpr), 1)}%."
            ),
            "chart_note": "Annual averages for both sexes. The participation rate is the cleaner structural signal, while labour force size is kept as a supporting graphic.",
            "datasets": [lfpr_dataset, labour_force_dataset],
            "main_dataset": lfpr_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Labour force count",
                    "value": compact_number(float(labour_force_dataset["data"][-1]["y"])),
                    "subtext": "Absolute labour force size in thousands.",
                    "dataset": labour_force_dataset,
                },
                {
                    "kind": "bars",
                    "title": "Participation milestones",
                    "value": latest_change(lfpr_dataset),
                    "subtext": "Start, latest and peak participation readings.",
                    "items": comparison_items(lfpr_dataset),
                    "color": colors["blue"],
                },
            ],
            "commentary": "A large labour-force headcount does not fully offset a softer participation rate, which is why ageing pressure matters for labour supply.",
            "sources": build_sources(["210-06101"], table_meta),
        }
    )

    unemployment = series_map["seasonally_adjusted_unemployment"]
    unemployment_peak_label, unemployment_peak = peak_point(unemployment)
    unemployment_trough_label, unemployment_trough = trough_point(unemployment)
    unemployment_dataset = frame_to_dataset("Seasonally adjusted unemployment rate", unemployment, colors["red"])
    analyses.append(
        {
            "id": "unemployment",
            "title": "Unemployment cycle",
            "headline": f"{unemployment.iloc[-1]['period_label']}: {fmt_number(latest_value(unemployment), 1)}% seasonally adjusted",
            "insight": (
                f"The seasonally adjusted unemployment rate ranged from {fmt_number(unemployment_trough, 1)}% in {unemployment_trough_label} "
                f"to {fmt_number(unemployment_peak, 1)}% in {unemployment_peak_label}."
            ),
            "chart_note": "Monthly moving 3-month series from the General Household Survey.",
            "datasets": [unemployment_dataset],
            "main_dataset": unemployment_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Recent cycle",
                    "value": recent_dataset(unemployment_dataset, 72)["data"][-1]["label"],
                    "subtext": "A zoomed view of the last 72 monthly observations.",
                    "dataset": recent_dataset(unemployment_dataset, 72),
                },
                {
                    "kind": "bars",
                    "title": "Shock snapshots",
                    "value": unemployment_dataset["data"][-1]["label"],
                    "subtext": "Nearest readings around major event markers plus the latest point.",
                    "items": event_snapshot_items(unemployment_dataset),
                    "color": colors["red"],
                },
            ],
            "commentary": "Unlike ageing or fertility, unemployment is sharply cyclical. The event markers matter here because labour-market stress tends to cluster around shocks.",
            "sources": build_sources(["210-06101"], table_meta),
        }
    )

    gdp_per_capita = series_map["real_gdp_per_capita"]
    real_gdp = series_map["real_gdp"]
    gdp_peak_label, gdp_peak = peak_point(gdp_per_capita)
    gdp_per_capita_dataset = frame_to_dataset("Real GDP per capita", gdp_per_capita, colors["indigo"])
    real_gdp_dataset = frame_to_dataset("Real GDP", real_gdp, colors["gold"])
    analyses.append(
        {
            "id": "gdp",
            "title": "Real GDP per capita",
            "headline": f"{gdp_per_capita.iloc[-1]['period_label']}: HK${fmt_number(latest_value(gdp_per_capita), 0)} per person in chained dollars",
            "insight": (
                f"Real GDP per capita climbed from HK${fmt_number(first_value(gdp_per_capita), 0)} to HK${fmt_number(latest_value(gdp_per_capita), 0)}. "
                f"The series high is HK${fmt_number(gdp_peak, 0)} in {gdp_peak_label}."
            ),
            "chart_note": "Annual chained-dollar GDP and real GDP per capita. Event lines are especially useful here because external crises show up clearly in the macro cycle.",
            "datasets": [gdp_per_capita_dataset, real_gdp_dataset],
            "main_dataset": gdp_per_capita_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Real GDP level",
                    "value": compact_number(float(real_gdp_dataset["data"][-1]["y"])),
                    "subtext": "Chained-dollar GDP level in HK$ million.",
                    "dataset": real_gdp_dataset,
                },
                {
                    "kind": "bars",
                    "title": "Decade growth",
                    "value": "Per-capita growth by decade",
                    "subtext": "Percentage change versus the previous decade anchor.",
                    "items": decade_change_items(gdp_per_capita_dataset, percent=True),
                    "color": colors["indigo"],
                },
            ],
            "commentary": "Per-capita output trends upward over the long run, but the distance between event markers and the line makes clear how exposed Hong Kong is to external shocks.",
            "sources": build_sources(["310-31001"], table_meta),
        }
    )

    cpi_yoy = series_map["cpi_yoy"]
    cpi_peak_label, cpi_peak = peak_point(cpi_yoy)
    cpi_trough_label, cpi_trough = trough_point(cpi_yoy)
    cpi_dataset = frame_to_dataset("Composite CPI YoY", cpi_yoy, colors["orange"])
    analyses.append(
        {
            "id": "inflation",
            "title": "Inflation regime",
            "headline": f"{cpi_yoy.iloc[-1]['period_label']}: {fmt_number(latest_value(cpi_yoy), 1)}% CPI inflation",
            "insight": (
                f"Composite CPI inflation ranged from {fmt_number(cpi_trough, 1)}% in {cpi_trough_label} "
                f"to {fmt_number(cpi_peak, 1)}% in {cpi_peak_label}."
            ),
            "chart_note": "Monthly year-on-year change in the Composite CPI.",
            "datasets": [cpi_dataset],
            "main_dataset": cpi_dataset,
            "support_charts": [
                {
                    "kind": "line",
                    "title": "Recent inflation window",
                    "value": recent_dataset(cpi_dataset, 60)["data"][-1]["label"],
                    "subtext": "The last 60 monthly observations for a cleaner recent read.",
                    "dataset": recent_dataset(cpi_dataset, 60),
                },
                {
                    "kind": "bars",
                    "title": "Event snapshots",
                    "value": cpi_dataset["data"][-1]["label"],
                    "subtext": "Nearest inflation readings around major event markers plus the latest point.",
                    "items": event_snapshot_items(cpi_dataset),
                    "color": colors["orange"],
                },
            ],
            "commentary": "Inflation in Hong Kong is better read as a sequence of regimes and shocks than as a smooth trend, which is why the event bars add useful context here.",
            "sources": build_sources(["510-60001"], table_meta),
        }
    )
    return analyses


def render_report(analyses: list[dict[str, Any]], changed_tables: list[str], table_meta: dict[str, tuple[dict[str, Any], dict[str, Any]]]) -> Path:
    rendered_analyses = [decorate_analysis(dict(analysis)) for analysis in analyses]
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "xml"]))
    template = env.get_template("report.html.j2")
    html = template.render(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        latest_release=max(comp["last_modified_date"] for comp, _ in table_meta.values()),
        changed_tables=changed_tables,
        analysis_count=len(analyses),
        analyses=rendered_analyses,
    )
    output_path = DIST_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def update_manifest(manifest: dict[str, Any], table_meta: dict[str, tuple[dict[str, Any], dict[str, Any]]], report_path: Path) -> None:
    manifest["checked_at_utc"] = datetime.now(UTC).isoformat()
    manifest["report_path"] = str(report_path.relative_to(ROOT))
    manifest["tables"] = {
        table_id: {
            "last_modified_date": comp["last_modified_date"],
            "title": lang["tb_title"],
            "source_url": TABLE_SOURCE_LINKS[table_id],
        }
        for table_id, (comp, lang) in table_meta.items()
    }
    write_manifest(manifest)


def sync_mobile_payload() -> Path:
    subprocess.run([sys.executable, str(MOBILE_EXPORT_SCRIPT)], check=True, cwd=ROOT)
    return ROOT / "android" / "src" / "data" / "reportData.json"


def run(force_refresh: bool, check_only: bool, skip_mobile_export: bool) -> dict[str, Any]:
    ensure_dirs()
    client = CenstatdClient()
    manifest = read_manifest()
    table_meta: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    changed_tables: list[str] = []

    for table_id in sorted({request.table_id for request in SERIES_REQUESTS}):
        comp = client.get_json(f"{BASE_URL}/data/table_{table_id}_comp.json")
        lang = client.get_json(f"{BASE_URL}/data/en/table_{table_id}_lang.json")
        table_dir = RAW_DIR / table_id
        table_dir.mkdir(exist_ok=True)
        (table_dir / "comp.json").write_text(json.dumps(comp, indent=2), encoding="utf-8")
        (table_dir / "lang.json").write_text(json.dumps(lang, indent=2), encoding="utf-8")
        previous_date = manifest.get("tables", {}).get(table_id, {}).get("last_modified_date")
        if force_refresh or previous_date != comp["last_modified_date"]:
            changed_tables.append(table_id)
        table_meta[table_id] = (comp, lang)

    if check_only:
        return {"changed_tables": changed_tables}

    effective_refresh = force_refresh or bool(changed_tables) or not (DIST_DIR / "index.html").exists()
    series_map = {request.name: extract_series(client, request, table_meta, effective_refresh) for request in SERIES_REQUESTS}
    analyses = build_analyses(series_map, table_meta)
    report_path = render_report(analyses, changed_tables, table_meta)
    update_manifest(manifest, table_meta, report_path)
    mobile_payload_path = None if skip_mobile_export else sync_mobile_payload()
    return {
        "changed_tables": changed_tables,
        "analysis_count": len(analyses),
        "report_path": report_path,
        "mobile_payload_path": mobile_payload_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local HK C&SD trend report.")
    parser.add_argument("--force-refresh", action="store_true", help="Refresh all cached source files before building.")
    parser.add_argument("--check-only", action="store_true", help="Only check whether any configured source tables changed.")
    parser.add_argument("--skip-mobile-export", action="store_true", help="Skip regenerating the Android app data payload.")
    args = parser.parse_args()

    result = run(force_refresh=args.force_refresh, check_only=args.check_only, skip_mobile_export=args.skip_mobile_export)
    if args.check_only:
        changed = result["changed_tables"]
        print("Updated tables available: " + ", ".join(changed) if changed else "No table updates detected.")
        return
    print(f"Built {result['analysis_count']} analyses.")
    print(f"Report: {result['report_path']}")
    if result["mobile_payload_path"]:
        print(f"Mobile payload: {result['mobile_payload_path']}")
    print("Updated source tables: " + ", ".join(result["changed_tables"]) if result["changed_tables"] else "No source date changes detected.")


if __name__ == "__main__":
    main()
