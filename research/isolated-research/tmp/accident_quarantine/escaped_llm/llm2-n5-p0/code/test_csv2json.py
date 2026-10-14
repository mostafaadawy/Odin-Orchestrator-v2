from csv2json import convert


def test_basic_conversion():
    csv_text = "name,age,city\nAlice,30,NYC\nBob,25,LA"
    result = convert(csv_text)
    assert len(result) == 2
    assert result[0] == {"name": "Alice", "age": "30", "city": "NYC"}
    assert result[1] == {"name": "Bob", "age": "25", "city": "LA"}


def test_single_row():
    csv_text = "name,age\nCharlie,35"
    result = convert(csv_text)
    assert len(result) == 1
    assert result[0] == {"name": "Charlie", "age": "35"}


def test_header_only():
    csv_text = "name,age,city"
    result = convert(csv_text)
    assert len(result) == 0


def test_empty_string():
    result = convert("")
    assert result == []


def test_whitespace_only():
    result = convert("   \n  ")
    assert result == []


def test_with_quoted_fields():
    csv_text = 'name,description\nAlice,"She said ""hello"""\nBob,Simple'
    result = convert(csv_text)
    assert len(result) == 2
    assert result[0]["name"] == "Alice"
    assert result[0]["description"] == 'She said "hello"'
    assert result[1]["name"] == "Bob"


def test_with_commas_in_fields():
    csv_text = 'name,address\nAlice,"123 Main St, Apt 4"\nBob,"456 Oak Ave, Apt 2"'
    result = convert(csv_text)
    assert len(result) == 2
    assert result[0]["address"] == "123 Main St, Apt 4"
    assert result[1]["address"] == "456 Oak Ave, Apt 2"


def test_with_empty_fields():
    csv_text = "name,age,city\nAlice,30,\nBob,,LA"
    result = convert(csv_text)
    assert len(result) == 2
    assert result[0] == {"name": "Alice", "age": "30", "city": ""}
    assert result[1] == {"name": "Bob", "age": "", "city": "LA"}


def test_with_newlines_in_fields():
    csv_text = 'name,description\nAlice,"Line 1\nLine 2"\nBob,Single'
    result = convert(csv_text)
    assert len(result) == 2
    assert result[0]["name"] == "Alice"
    assert "Line 1" in result[0]["description"]
    assert "Line 2" in result[0]["description"]


if __name__ == "__main__":
    test_basic_conversion()
    test_single_row()
    test_header_only()
    test_empty_string()
    test_whitespace_only()
    test_with_quoted_fields()
    test_with_commas_in_fields()
    test_with_empty_fields()
    test_with_newlines_in_fields()
    print("PASS")
