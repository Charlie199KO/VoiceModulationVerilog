`timescale 1ns/1ps
// Board-independent top-level wrapper for simulation and future FPGA use.
module top_module (
    input wire clk,
    input wire rst,
    input wire sample_valid,
    input wire signed [15:0] sample_in,
    input wire [2:0] mode,
    input wire [2:0] volume_level,
    input wire [11:0] echo_delay_samples,
    input wire [15:0] echo_gain_q15,
    input wire [15:0] ring_half_period_samples,
    output wire signed [15:0] sample_out,
    output wire out_valid
);
    voice_dsp_core u_voice_dsp_core (
        .clk(clk),
        .rst(rst),
        .sample_valid(sample_valid),
        .sample_in(sample_in),
        .mode(mode),
        .volume_level(volume_level),
        .echo_delay_samples(echo_delay_samples),
        .echo_gain_q15(echo_gain_q15),
        .ring_half_period_samples(ring_half_period_samples),
        .sample_out(sample_out),
        .out_valid(out_valid)
    );
endmodule
