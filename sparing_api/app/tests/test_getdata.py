from app.api.routers.getdata import _num


def test_num_valid_string_parsed():
    assert _num({"ph": "7.2"}, ("pH", "ph"), lo=0, hi=14) == (7.2, False)


def test_num_alias_order_first_present_wins():
    assert _num({"pH": 8, "ph": 9}, ("pH", "ph")) == (8.0, False)


def test_num_zero_not_treated_as_missing():
    # regression: the old `d.get("x") or d.get("y")` treated 0 as absent
    assert _num({"debit": 0}, ("debit", "Debit"), lo=0) == (0.0, False)


def test_num_missing_is_none_not_dropped():
    assert _num({}, ("ph", "pH")) == (None, False)


def test_num_out_of_upper_bound_dropped():
    assert _num({"ph": 15}, ("pH", "ph"), lo=0, hi=14) == (None, True)


def test_num_below_lower_bound_dropped():
    assert _num({"cod": -5}, ("cod", "COD"), lo=0) == (None, True)


def test_num_non_numeric_dropped():
    assert _num({"tss": "abc"}, ("tss", "TSS"), lo=0) == (None, True)


def test_num_no_bounds_passes_any_number():
    assert _num({"voltage": 230.5}, ("voltage", "Voltage")) == (230.5, False)
