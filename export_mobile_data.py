from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import build_report as web_report


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_PATH = ROOT / "android" / "src" / "data" / "reportData.json"


class LocalCacheClient:
    def __init__(self) -> None:
        self._sd_map = {
            "1": {"obs_value_suppressed": "1"},
            "2": {"obs_value_suppressed": "1"},
            "3": {"obs_value_suppressed": "1"},
            "4": {"obs_value_suppressed": "1"},
            "5": {"obs_value_suppressed": "1"},
            "6": {"obs_value_suppressed": "1"},
            "7": {"obs_value_suppressed": "1"},
            "8": {"obs_value_suppressed": "1"},
            "9": {"obs_value_suppressed": "1"},
            "10": {"obs_value_suppressed": "1"},
            "11": {"obs_value_suppressed": "1"},
            "12": {"obs_value_suppressed": "1"},
        }

    def get_sd_map(self) -> dict[str, dict[str, Any]]:
        return self._sd_map

    def get_text(self, url: str) -> str:
        raise FileNotFoundError(f"Offline export expected cached series file for {url}")


def load_table_meta() -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    table_meta: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for request in web_report.SERIES_REQUESTS:
        if request.table_id in table_meta:
            continue
        table_dir = RAW_DIR / request.table_id
        comp = json.loads((table_dir / "comp.json").read_text(encoding="utf-8"))
        lang = json.loads((table_dir / "lang.json").read_text(encoding="utf-8"))
        table_meta[request.table_id] = (comp, lang)
    return table_meta


def build_stats(main_dataset: dict[str, Any]) -> list[dict[str, str]]:
    peak = web_report.peak_dataset_point(main_dataset)
    return [
        {"label": "Coverage", "value": f"{main_dataset['data'][0]['label']} to {main_dataset['data'][-1]['label']}"},
        {"label": "Latest", "value": web_report.compact_number(float(main_dataset['data'][-1]['y']))},
        {"label": "Change", "value": web_report.latest_change(main_dataset)},
        {
            "label": "Peak",
            "value": f"{web_report.compact_number(float(peak['y']))} | {peak['label']}",
        },
    ]


def build_payload() -> dict[str, Any]:
    client = LocalCacheClient()
    table_meta = load_table_meta()
    series_map = {
        request.name: web_report.extract_series(client, request, table_meta, force_refresh=False)
        for request in web_report.SERIES_REQUESTS
    }
    analyses = web_report.build_analyses(series_map, table_meta)
    sections = []
    for analysis in analyses:
        section = dict(analysis)
        main_dataset = section.pop("main_dataset")
        section["main_dataset_label"] = main_dataset["label"]
        section["stats"] = build_stats(main_dataset)
        sections.append(section)

    return {
        "app_title": "HK Census",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "latest_release": max(comp["last_modified_date"] for comp, _ in table_meta.values()),
        "sections": sections,
    }


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
