"""Compact immutable record types shared by static data modules."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, ClassVar


class Record:
    """Provide lightweight mapping-style compatibility for rule algorithms."""

    __slots__ = ()
    _aliases: ClassVar[dict[str, str]] = {}

    def __getitem__(self, key: str) -> Any:
        return getattr(self, self._aliases.get(key, key))

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, self._aliases.get(key, key), default)

    def keys(self) -> tuple[str, ...]:
        return tuple(field.name for field in fields(self))


@dataclass(frozen=True, slots=True)
class HazardData(Record):
    """A complete hazard rule and its sampling-device configuration."""

    basis: str
    storage: str
    collector: str
    analysis_group: str
    flow_rates: str
    point_device: str
    point_flow_rate: str
    point_device_range: str
    individual_device: str
    individual_flow_rate: str
    individual_device_range: str
    display_name: str = ""
    category: str = "chemical"
    sampling_policy: str = "default"
    default_individual_sampling_time: str = ""
    full_measure_below_hours: str = ""
    method: str = ""

    _aliases: ClassVar[dict[str, str]] = {
        "空气收集器": "collector",
        "定点采样设备": "point_device",
        "定点采样流量": "point_flow_rate",
        "定点设备流量范围": "point_device_range",
        "个体采样设备": "individual_device",
        "个体采样流量": "individual_flow_rate",
        "个体设备流量范围": "individual_device_range",
    }


@dataclass(frozen=True, slots=True)
class CollectorCapability(Record):
    supports_individual: bool = True
    point_sampling_time: str = ""


@dataclass(frozen=True, slots=True)
class OELRule(Record):
    project: str
    limit_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParsingRules(Record):
    ignored_projects: tuple[str, ...]
    detail_stop_markers: tuple[str, ...]
    workbench_suffix: str
    detail_preferred_exposure_type: str


@dataclass(frozen=True, slots=True)
class CompositionRules(Record):
    placeholder_markers: tuple[str, ...]
    ignored_components: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CountThreshold(Record):
    maximum_people: int | None
    count: int

    _aliases: ClassVar[dict[str, str]] = {
        "points": "count",
        "objects": "count",
    }


@dataclass(frozen=True, slots=True)
class SamplingRules(Record):
    mobile_job_type: str
    individual_target: str
    point_mode: str
    individual_mode: str
    physical_limit_type: str
    point_limit_type: str
    individual_limit_type: str
    direct_read_time_type: str
    short_time_type: str
    long_time_type: str
    point_sampling_time: str
    individual_sampling_time: str
    dust_filter_keyword: str
    limit_types: tuple[str, ...]
    daily_points_by_people_per_shift: tuple[CountThreshold, ...]
    daily_objects_by_people_per_shift: tuple[CountThreshold, ...]
    daily_times: dict[str, int]
    detection_days: dict[str, int]


@dataclass(frozen=True, slots=True)
class DocumentRules(Record):
    fill_font_name: str
    fill_east_asia_font: str
    fill_font_size_pt: float
    detection_type_options: tuple[str, ...]
    table3_widths_cm: dict[str, float]


@dataclass(frozen=True, slots=True)
class ReportRules(Record):
    parsing: ParsingRules
    composition: CompositionRules
    sampling: SamplingRules
    document: DocumentRules
