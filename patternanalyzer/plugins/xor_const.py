"""XOR constant transform plugin."""

from ..plugin_api import BytesView, TransformPlugin


class XOPlugin(TransformPlugin):
    """XOR transform plugin that applies constant XOR to bytes."""

    def describe(self) -> str:
        """Return plugin description."""
        return "Applies XOR transformation with constant value"

    def run(self, data: BytesView, params: dict) -> BytesView:
        """Apply XOR transformation."""
        xor_value = params.get('xor_value', 0x00)
        if not isinstance(xor_value, int) or not (0 <= xor_value <= 255):
            raise ValueError("xor_value must be an integer between 0 and 255")

        # Convert to bytes and apply XOR
        transformed = bytes(b ^ xor_value for b in data.to_bytes())
        return BytesView(transformed)