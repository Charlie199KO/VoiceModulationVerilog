# Future FPGA Integration Plan

The current release does not require an FPGA. The Verilog core is board-independent and has a sample-valid interface.

A physical implementation would require:

1. A selected FPGA development board.
2. A compatible audio codec or external ADC/DAC.
3. I2S receiver and transmitter (if required by the codec).
4. Clock generation and clock-domain crossing between the audio clock and FPGA system clock.
5. Input/output buffering.
6. Board-specific pin constraints and timing constraints.
7. Hardware verification using continuous audio and FIFO status counters.

Do not invent pin mappings before selecting the FPGA board and audio codec. The first physical milestone should be audio pass-through, followed by Robot, Echo, Radio and Volume effects.
