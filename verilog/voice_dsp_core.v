`timescale 1ns/1ps
module voice_dsp_core (
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
    wire signed [15:0] bypass_value;
    wire signed [15:0] robot_value;
    wire signed [15:0] echo_value;
    wire signed [15:0] radio_value;
    wire signed [15:0] volume_value;
    wire bypass_valid;
    wire robot_valid;
    wire echo_valid;
    wire radio_valid;
    wire volume_valid;
    reg [2:0] mode_d;

    bypass u_bypass (
        .clk(clk), .rst(rst), .sample_valid(sample_valid),
        .sample_in(sample_in), .sample_out(bypass_value), .out_valid(bypass_valid)
    );

    ring_modulator u_ring_modulator (
        .clk(clk), .rst(rst), .sample_valid(sample_valid),
        .sample_in(sample_in), .half_period_samples(ring_half_period_samples),
        .sample_out(robot_value), .out_valid(robot_valid)
    );

    echo_unit u_echo_unit (
        .clk(clk), .rst(rst), .sample_valid(sample_valid),
        .sample_in(sample_in), .delay_samples(echo_delay_samples),
        .echo_gain_q15(echo_gain_q15), .sample_out(echo_value), .out_valid(echo_valid)
    );

    radio_filter u_radio_filter (
        .clk(clk), .rst(rst), .sample_valid(sample_valid),
        .sample_in(sample_in), .sample_out(radio_value), .out_valid(radio_valid)
    );

    volume_control u_volume_control (
        .clk(clk), .rst(rst), .sample_valid(sample_valid),
        .sample_in(sample_in), .volume_level(volume_level),
        .sample_out(volume_value), .out_valid(volume_valid)
    );

    // Register mode alongside the registered effect outputs.
    always @(posedge clk) begin
        if (rst)
            mode_d <= 3'd0;
        else if (sample_valid)
            mode_d <= mode;
    end

    mode_selector u_mode_selector (
        .mode(mode_d),
        .bypass_value(bypass_value),
        .robot_value(robot_value),
        .echo_value(echo_value),
        .radio_value(radio_value),
        .volume_value(volume_value),
        .selected_value(sample_out)
    );

    // Every effect module receives the same valid stream and has one-cycle
    // registered output latency. The bypass valid signal is therefore the
    // common output-valid signal.
    assign out_valid = bypass_valid;
endmodule
