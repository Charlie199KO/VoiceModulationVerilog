import unittest
import numpy as np

from python.fixed_point import pcm16_to_hex, hex_to_pcm16, float_to_int16, int16_to_float


class FixedPointConversionTests(unittest.TestCase):
    def test_hex_round_trip(self):
        for value in [-32768, -12345, -1, 0, 1, 12345, 32767]:
            self.assertEqual(hex_to_pcm16(pcm16_to_hex(value)), value)

    def test_float_pcm_round_trip(self):
        source = np.array([-32768, -12345, -1, 0, 1, 12345, 32767], dtype=np.int16)
        converted = float_to_int16(int16_to_float(source))
        np.testing.assert_array_equal(converted, source)


if __name__ == "__main__":
    unittest.main()
