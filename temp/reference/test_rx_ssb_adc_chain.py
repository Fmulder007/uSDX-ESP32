"""Integration tests for the ADC-event RX SSB reference pipeline."""

import unittest

from rx_ssb_adc_chain import RxSsbAdcReferencePipeline


class TestRxSsbAdcReferencePipeline(unittest.TestCase):
    def test_audio_output_is_emitted_once_per_eight_timer_events(self):
        pipeline = RxSsbAdcReferencePipeline(startup_adc_register=0)
        outputs = []
        for tick in range(17):
            result = pipeline.push_timer_event(
                i_sample_at_tick=tick * 10,
                q_sample_at_tick=tick * 20,
            )
            if result is not None:
                outputs.append(result)
        self.assertEqual(len(outputs), 3)

    def test_adc_mux_pipeline_is_connected_to_cic_state_machine(self):
        pipeline = RxSsbAdcReferencePipeline(startup_adc_register=0)
        for tick in range(8):
            pipeline.push_timer_event(
                i_sample_at_tick=100 + tick,
                q_sample_at_tick=200 + tick,
            )
        self.assertEqual(pipeline.adc_input.phase, 0)
        self.assertEqual(pipeline.ssb_chain.cic.phase, 0)
        self.assertEqual(pipeline.ssb_chain.cic.i_s0za1, 102)
        self.assertEqual(pipeline.ssb_chain.cic.q_s0za1, 206)

    def test_audio_output_range(self):
        pipeline = RxSsbAdcReferencePipeline()
        outputs = []
        for tick in range(1024):
            result = pipeline.push_timer_event(
                i_sample_at_tick=((tick * 37) % 1024) - 512,
                q_sample_at_tick=((tick * 53) % 1024) - 512,
            )
            if result is not None:
                outputs.append(result.audio_sample)
        self.assertTrue(outputs)
        self.assertTrue(all(-512 <= sample <= 511 for sample in outputs))


    def test_nr_and_ssb_iir_options_reach_adc_pipeline_post_stage(self):
        pipeline = RxSsbAdcReferencePipeline(
            startup_adc_register=0,
            volume=13,
            agc=0,
            nr=1,
            filt=1,
        )
        outputs = []
        for tick in range(256):
            result = pipeline.push_timer_event(
                i_sample_at_tick=((tick * 37) % 1024) - 511,
                q_sample_at_tick=((tick * 53) % 1024) - 511,
            )
            if result is not None:
                outputs.append(result.audio_sample)

        self.assertTrue(outputs)
        self.assertEqual(pipeline.ssb_chain.nr, 1)
        self.assertEqual(pipeline.ssb_chain.filt, 1)
        self.assertNotEqual(pipeline.ssb_chain.post.nr_state.ea1, 0)
        self.assertNotEqual(pipeline.ssb_chain.post.iir_state.zb1, 0)
        self.assertTrue(all(-512 <= sample <= 511 for sample in outputs))


if __name__ == "__main__":
    unittest.main()
