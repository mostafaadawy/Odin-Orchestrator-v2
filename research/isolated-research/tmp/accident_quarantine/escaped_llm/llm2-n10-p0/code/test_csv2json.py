from csv2json import convert


def test_basic_conversion():
    csv_text = "name,age,city\nAlice,30,New York\nBob,25,Los Angeles"
    expected = [
        {'name': 'Alice', 'age': '30', 'city': 'New York'},
        {'name': 'Bob', 'age': '25', 'city': 'Los Angeles'}
    ]
    assert convert(csv_text) == expected


def test_empty_input():
    assert convert("") == []
    assert convert("\n\n") == []


def test_header_only():
    csv_text = "name,age,city"
    assert convert(csv_text) == []


def test_whitespace_handling():
    csv_text = "name , age , city\nAlice , 30 , New York"
    expected = [
        {'name': 'Alice', 'age': '30', 'city': 'New York'}
    ]
    assert convert(csv_text) == expected


def test_single_row():
    csv_text = "id,value\n123,test"
    expected = [
        {'id': '123', 'value': 'test'}
    ]
    assert convert(csv_text) == expected


def test_special_characters():
    csv_text = "name,email\nJohn Doe,john@example.com\nJane Smith,jane@example.com"
    expected = [
        {'name': 'John Doe', 'email': 'john@example.com'},
        {'name': 'Jane Smith', 'email': 'jane@example.com'}
    ]
    assert convert(csv_text) == expected


if __name__ == "__main__":
    test_basic_conversion()
    test_empty_input()
    test_header_only()
    test_whitespace_handling()
    test_single_row()
    test_special_characters()
    print("PASS")
