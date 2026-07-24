from scripts import REPORTS_ROOT

from data_store.hazards import HAZARDS
from data_store.oel_limits import OEL_INDEX


def test_repository_data_store_is_available_to_report_verify():
    assert (REPORTS_ROOT / "data_store").is_dir()
    assert "甲苯" in HAZARDS
    assert "甲苯" in OEL_INDEX
