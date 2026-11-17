import unittest
import numpy as np

from python import config
from python.dsp_effects import EffectParameters, FixedPointDSP


class FixedPointDSPTests(unittest.TestCase):
    def test_bypass_is_exact(self):
        samples = np.array([0, 1, -1, 1234, -2345, 32767, -32768], dtype=np.int16)
        output = FixedPointDSP().process_block(samples, config.MODE_BYPASS)
        np.testing.assert_array_equal(output, samples)

    def test_volume_modes(self):
        samples = np.array([4000, -4000, 32767, -32768], dtype=np.int16)
        dsp = FixedPointDSP()
        self.assertEqual(dsp.process_block(samples, config.MODE_VOLUME,
                                           EffectParameters(volume_level=0)).tolist(), [0, 0, 0, 0])
        dsp.reset()
        self.assertEqual(dsp.process_block(samples, config.MODE_VOLUME,
                                           EffectParameters(volume_level=2)).tolist(), [2000, -2000, 16383, -16384])
        dsp.reset()
        self.assertEqual(dsp.process_block(samples, config.MODE_VOLUME,
                                           EffectParameters(volume_level=4)).tolist(), [8000, -8000, 32767, -32768])

    def test_echo_starts_without_old_samples(self):
        samples = np.array([1000, 0, 0, 0], dtype=np.int16)
        params = EffectParameters(echo_delay_samples=2, echo_gain_q15=16384)
        output = FixedPointDSP().process_block(samples, config.MODE_ECHO, params)
        self.assertEqual(output[0], 1000)
        self.assertEqual(output[1], 0)
        self.assertEqual(output[2], 500)

    def test_ring_modulator_alternates_after_half_period(self):
        samples = np.array([100, 100, 100, 100, 100, 100], dtype=np.int16)
        params = EffectParameters(ring_half_period_samples=2)
        output = FixedPointDSP().process_block(samples, config.MODE_ROBOT, params)
        self.assertEqual(output.tolist(), [100, 100, -100, -100, 100, 100])

    def test_radio_filter_is_bounded(self):
        samples = np.resize(np.array([32767, -32768], dtype=np.int16), 1000)
        output = FixedPointDSP().process_block(samples, config.MODE_RADIO)
        self.assertTrue(np.all(output <= 32767))
        self.assertTrue(np.all(output >= -32768))


if __name__ == "__main__":
    unittest.main()
