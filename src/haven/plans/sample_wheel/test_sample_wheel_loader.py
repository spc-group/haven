import pytest
from sample_wheel_reader import clean_column_names, convert_energy_range

# Tests for clean_column_names
def test_clean_column_names():
    columns = ["File Name", "Element_Symbol?", "Absorption.Edge!", "Sample Name"]
    expected = ["file_name", "element_symbol", "absorptionedge", "sample_name"]
    assert clean_column_names(columns) == expected

def test_clean_column_names_with_special_chars():
    columns = ["Column with space and ? mark!", "Another.Column-Name"]
    expected = ["column_with_space_and__mark", "anothercolumnname"]
    assert clean_column_names(columns) == expected

def test_clean_column_names_no_special_chars():
    columns = ["normal_column", "anotherOne"]
    expected = ["normal_column", "anotherone"]
    assert clean_column_names(columns) == expected

# Tests for convert_energy_range
def test_convert_energy_range():
    energy_range_str = "-200 -30 -10 25 15k"
    expected = [-200, -30, -10, 25, (15 / 0.512) ** 2]
    assert convert_energy_range(energy_range_str) == expected

def test_convert_energy_range_no_k():
    energy_range_str = "100 200 300"
    expected = [100, 200, 300]
    assert convert_energy_range(energy_range_str) == expected

def test_convert_energy_range_only_k():
    energy_range_str = "1k 2k 3k"
    expected = [(1 / 0.512) ** 2, (2 / 0.512) ** 2, (3 / 0.512) ** 2]
    assert convert_energy_range(energy_range_str) == expected

def test_convert_energy_range_invalid():
    energy_range_str = "-100 abc 5k"
    with pytest.raises(ValueError):
        convert_energy_range(energy_range_str)
