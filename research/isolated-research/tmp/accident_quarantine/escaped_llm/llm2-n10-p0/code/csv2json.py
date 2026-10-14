def convert(text):
    """Convert CSV text with header row to list of dictionaries."""
    lines = text.strip().split('\n')
    if not lines or not lines[0]:
        return []

    headers = [h.strip() for h in lines[0].split(',')]
    result = []

    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(',')]
        if len(values) == len(headers):
            row_dict = dict(zip(headers, values))
            result.append(row_dict)

    return result
