"""Tests for XOR constant transform plugin."""

import pytest
from patternlab.plugins.xor_const import XOPlugin
from patternlab.plugin_api import BytesView


class TestXOPlugin:
    """Test cases for XOPlugin."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = XOPlugin()
        self.test_data = b"Hello, World! This is a test."

    def test_describe(self):
        """Test plugin description."""
        desc = self.plugin.describe()
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_xor_55_basic(self):
        """Test XOR with 0x55 on small byte sequence."""
        data = BytesView(b'\x00\x55\xAA\xFF')
        params = {'xor_value': 0x55}

        result = self.plugin.run(data, params)
        expected = bytes(b ^ 0x55 for b in data.to_bytes())

        assert result.to_bytes() == expected

    def test_xor_55_larger_data(self):
        """Test XOR with 0x55 on larger data."""
        data = BytesView(self.test_data)
        params = {'xor_value': 0x55}

        result = self.plugin.run(data, params)
        expected = bytes(b ^ 0x55 for b in data.to_bytes())

        assert result.to_bytes() == expected

    def test_invertibility(self):
        """Test that XOR is invertible."""
        data = BytesView(self.test_data)
        params = {'xor_value': 0xAA}

        # Apply XOR twice
        result1 = self.plugin.run(data, params)
        result2 = self.plugin.run(result1, params)

        # Should return original data
        assert result2.to_bytes() == data.to_bytes()

    def test_different_xor_values(self):
        """Test different XOR values."""
        data = BytesView(b'\x12\x34\x56\x78')

        for xor_val in [0x00, 0xFF, 0x42, 0x99]:
            params = {'xor_value': xor_val}
            result = self.plugin.run(data, params)
            expected = bytes(b ^ xor_val for b in data.to_bytes())
            assert result.to_bytes() == expected

    def test_invalid_xor_value(self):
        """Test invalid XOR values."""
        data = BytesView(b'test')

        # Test negative value
        with pytest.raises(ValueError):
            self.plugin.run(data, {'xor_value': -1})

        # Test value > 255
        with pytest.raises(ValueError):
            self.plugin.run(data, {'xor_value': 256})

        # Test non-integer value
        with pytest.raises(ValueError):
            self.plugin.run(data, {'xor_value': 'invalid'})

    def test_empty_data(self):
        """Test with empty data."""
        data = BytesView(b'')
        params = {'xor_value': 0x55}

        result = self.plugin.run(data, params)
        assert result.to_bytes() == b''