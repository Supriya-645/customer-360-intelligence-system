from src.decision.decision_engine import evaluate


def _profile(**overrides):
    base = {
        "risk_score": 20,
        "risk_band": "Low Risk",
        "collection_priority_score": 5,
        "cross_sell_eligible": True,
        "behavioral_score": 90,
        "behavioral_band": "Strong",
        "health_segment": "Healthy",
        "num_late_payments": 0,
        "num_missed_payments": 0,
        "avg_dpd_overall": 0,
        "lateness_trend": 0,
        "dpd_trend": 0,
        "utilization_trend": 0,
    }
    base.update(overrides)
    return base


def test_high_risk_routes_to_collection_intervention():
    decision = evaluate(_profile(risk_band="High Risk", risk_score=75, avg_dpd_overall=15, num_missed_payments=2))
    assert decision.recommended_action == "COLLECTION_INTERVENTION"
    assert "HIGH_DPD" in decision.reason_codes
    assert "MISSED_PAYMENTS" in decision.reason_codes


def test_urgent_collection_priority_overrides_low_risk_band():
    # even a Low Risk band should still route to intervention if collection priority is URGENT
    decision = evaluate(_profile(risk_band="Low Risk", collection_priority_score=40))
    assert decision.recommended_action == "COLLECTION_INTERVENTION"


def test_medium_risk_routes_to_manual_review():
    decision = evaluate(_profile(risk_band="Medium Risk", risk_score=45))
    assert decision.recommended_action == "MANUAL_REVIEW"


def test_low_risk_and_eligible_routes_to_cross_sell():
    decision = evaluate(_profile(risk_band="Low Risk", cross_sell_eligible=True))
    assert decision.recommended_action == "CROSS_SELL_OPPORTUNITY"
    assert decision.cross_sell_opportunity == "ELIGIBLE"


def test_low_risk_but_not_eligible_routes_to_retention():
    decision = evaluate(_profile(risk_band="Low Risk", cross_sell_eligible=False, num_late_payments=1))
    assert decision.recommended_action == "RETENTION_ENGAGEMENT"


def test_worsening_trends_produce_reason_codes():
    decision = evaluate(_profile(risk_band="High Risk", lateness_trend=5, dpd_trend=3, utilization_trend=0.1))
    assert "WORSENING_PAYMENT_TREND" in decision.reason_codes
    assert "WORSENING_DPD_TREND" in decision.reason_codes
    assert "RISING_UTILIZATION" in decision.reason_codes


def test_decision_always_has_at_least_one_reason_code():
    for risk_band in ("Low Risk", "Medium Risk", "High Risk"):
        decision = evaluate(_profile(risk_band=risk_band))
        assert len(decision.reason_codes) > 0


def test_to_dict_has_expected_keys():
    decision = evaluate(_profile())
    d = decision.to_dict()
    assert set(d.keys()) == {
        "risk_band", "collection_priority", "cross_sell_opportunity",
        "behavioral_band", "health_segment", "recommended_action", "reason_codes",
    }
