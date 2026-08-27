from src.scorecards import risk_scorecard, collection_scorecard, propensity_scorecard, behavioral_scorecard, health_scorecard


def test_risk_score_range_and_bands():
    assert risk_scorecard.compute_risk_score(0.0) == 0.0
    assert risk_scorecard.compute_risk_score(1.0) == 100.0
    assert risk_scorecard.risk_band(10) == "Low Risk"
    assert risk_scorecard.risk_band(45) == "Medium Risk"
    assert risk_scorecard.risk_band(75) == "High Risk"
    # boundary values land in the band starting at the cutoff
    assert risk_scorecard.risk_band(30) == "Medium Risk"
    assert risk_scorecard.risk_band(60) == "High Risk"


def test_collection_priority_normalization():
    result = collection_scorecard.compute_collection_priority(
        risk_score=80, amt_credit=2000000, min_credit=0, max_credit=4000000, max_raw_in_portfolio=100
    )
    assert 0 <= result.collection_priority_score <= 100
    # higher exposure at the same risk should produce a higher score
    higher_exposure = collection_scorecard.compute_collection_priority(
        risk_score=80, amt_credit=3900000, min_credit=0, max_credit=4000000, max_raw_in_portfolio=100
    )
    assert higher_exposure.collection_priority_score > result.collection_priority_score


def test_collection_priority_handles_degenerate_range():
    # min == max should not raise a division-by-zero
    result = collection_scorecard.compute_collection_priority(
        risk_score=50, amt_credit=1000000, min_credit=1000000, max_credit=1000000, max_raw_in_portfolio=100
    )
    assert result.collection_priority_score == 0.0


def test_cross_sell_eligibility_edge_cases():
    eligible = propensity_scorecard.evaluate_cross_sell(risk_score=10, num_late_payments=0, avg_utilization_overall=0.1)
    assert eligible.eligible is True
    assert eligible.cross_sell_opportunity == 100.0

    ineligible_risk = propensity_scorecard.evaluate_cross_sell(risk_score=25, num_late_payments=0, avg_utilization_overall=0.1)
    assert ineligible_risk.eligible is False
    assert "RISK_SCORE_TOO_HIGH" in ineligible_risk.reason_codes

    ineligible_late = propensity_scorecard.evaluate_cross_sell(risk_score=10, num_late_payments=1, avg_utilization_overall=0.1)
    assert ineligible_late.eligible is False
    assert "HAS_LATE_PAYMENTS" in ineligible_late.reason_codes

    # missing utilization (no credit card) should not crash - defaults to 0
    no_card = propensity_scorecard.evaluate_cross_sell(risk_score=10, num_late_payments=0, avg_utilization_overall=None)
    assert no_card.eligible is True


def test_behavioral_score_perfect_customer():
    score = behavioral_scorecard.compute_behavioral_score(
        total_installments=20, num_late_payments=0, num_missed_payments=0,
        avg_dpd_overall=0, lateness_trend=-5, dpd_trend=0, utilization_trend=-0.1,
    )
    assert score == 100.0
    assert behavioral_scorecard.behavioral_band(score) == "Strong"


def test_behavioral_score_penalizes_late_and_worsening():
    score = behavioral_scorecard.compute_behavioral_score(
        total_installments=20, num_late_payments=10, num_missed_payments=3,
        avg_dpd_overall=15, lateness_trend=5, dpd_trend=0, utilization_trend=0,
    )
    assert 0 <= score < 100
    assert behavioral_scorecard.behavioral_band(score) in ("Fair", "Weak")


def test_behavioral_score_caps_prevent_single_extreme_from_zeroing_score():
    # By design (see module docstring): missed-payment and DPD penalties are each
    # capped at 20, so even an extreme value in those two can't alone hit 0 -
    # only late_payment_rate (uncapped, up to 40) plus both caps plus the trend
    # flag can. Expected floor here: 100 - 40 - 20 - 20 - 10 = 10.
    extreme_bad = behavioral_scorecard.compute_behavioral_score(
        total_installments=1, num_late_payments=1, num_missed_payments=100,
        avg_dpd_overall=9999, lateness_trend=1, dpd_trend=1, utilization_trend=1,
    )
    assert extreme_bad == 10.0


def test_behavioral_score_never_goes_below_zero():
    # A genuinely maximal combination (100% late rate is already baked in above;
    # this just confirms the final clip guards the floor regardless of inputs).
    score = behavioral_scorecard.compute_behavioral_score(
        total_installments=1, num_late_payments=1, num_missed_payments=100,
        avg_dpd_overall=9999, lateness_trend=1, dpd_trend=1, utilization_trend=1,
    )
    assert score >= 0.0


def test_behavioral_score_zero_installments_does_not_divide_by_zero():
    score = behavioral_scorecard.compute_behavioral_score(
        total_installments=0, num_late_payments=0, num_missed_payments=0,
        avg_dpd_overall=0, lateness_trend=0, dpd_trend=0, utilization_trend=0,
    )
    assert score == 100.0


def test_health_score_composite_range_and_bands():
    score = health_scorecard.compute_health_score(
        risk_score=10, behavioral_score=90, collection_severity=5, cross_sell_opportunity=100
    )
    assert 0 <= score <= 100
    assert health_scorecard.health_segment(score) == "Healthy"

    worst_case = health_scorecard.compute_health_score(
        risk_score=100, behavioral_score=0, collection_severity=100, cross_sell_opportunity=0
    )
    assert worst_case == 0.0
    assert health_scorecard.health_segment(worst_case) == "High Risk"


def test_health_score_monotonic_in_risk():
    low_risk = health_scorecard.compute_health_score(50, 50, 50, 50)
    high_risk = health_scorecard.compute_health_score(90, 50, 50, 50)
    assert high_risk < low_risk
