from src.taxonomy.domains import classify_by_keyword


def test_safety_query():
    assert classify_by_keyword("how do I apply lockout tagout before maintenance") == "Safety"


def test_maintenance_query():
    assert classify_by_keyword("how do I replace the drive bearing on the press") == "Maintenance"


def test_qc_query():
    assert classify_by_keyword("what is the bore diameter tolerance for the bearing housing") == "QualityControl"


def test_ambiguous_returns_none():
    result = classify_by_keyword("what time does the shift start")
    assert result is None


def test_no_match_returns_none():
    result = classify_by_keyword("the weather is nice today")
    assert result is None
