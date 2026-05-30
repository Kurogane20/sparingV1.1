from app.utils.device_secret import generate_device_secret, mask_secret

def test_generate_device_secret_length():
    s = generate_device_secret()
    assert len(s) == 64

def test_generate_device_secret_hex():
    s = generate_device_secret()
    int(s, 16)  # raises ValueError if not valid hex

def test_generate_device_secret_unique():
    a = generate_device_secret()
    b = generate_device_secret()
    assert a != b

def test_mask_secret_short():
    assert mask_secret("abcdef") == "abcd••••"

def test_mask_secret_normal():
    s = "a" * 64
    result = mask_secret(s)
    assert result.startswith("aaaa")
    assert "•" in result
    assert result.endswith("••••")

def test_mask_secret_empty():
    assert mask_secret("") == "••••••••"
