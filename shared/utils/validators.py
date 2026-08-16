def validate_keys(data, required_keys):
    return all(key in data for key in required_keys)
