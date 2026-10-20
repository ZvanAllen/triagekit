from triagekit.detectors import detect_comorbidity, detect_maintenance_treatment
from triagekit.factory import build_clinic_engine


def cfg():
    return build_clinic_engine().config


def test_comorbidity_from_meds():
    assert detect_comorbidity("Metformin 500mg", "", cfg()) is True


def test_comorbidity_from_history():
    assert detect_comorbidity("", "Type 2 diabetes", cfg()) is True


def test_mental_health_med_is_not_a_comorbidity():
    # SSRIs must not trip comorbidity detection.
    assert detect_comorbidity("Sertraline 50mg daily", "", cfg()) is False


def test_no_comorbidity_on_empty():
    assert detect_comorbidity("", "", cfg()) is False


def test_treatment_detection():
    assert detect_maintenance_treatment("Semaglutide 1mg weekly", cfg()) is True
    assert detect_maintenance_treatment("Liraglutide 3mg", cfg()) is True


def test_treatment_absent():
    assert detect_maintenance_treatment("Vitamin D", cfg()) is False
    assert detect_maintenance_treatment("", cfg()) is False
