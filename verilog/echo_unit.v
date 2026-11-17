`timescale 1ns/1ps
// Fixed-depth circular delay buffer with Q1.15 echo gain.
// delay_samples=1 adds the immediately previous input sample.
module echo_unit #(
    parameter ADDR_WIDTH = 12,
    parameter DEPTH = 4096
) (
    input wire clk,
    input wire rst,
    input wire sample_valid,
    input wire signed [15:0] sample_in,
    input wire [11:0] delay_samples,
    input wire [15:0] echo_gain_q15,
    output reg signed [15:0] sample_out,
    output reg out_valid
);
    reg signed [15:0] delay_mem [0:DEPTH-1];
    reg [ADDR_WIDTH-1:0] write_ptr;
    integer i;

    wire [11:0] safe_delay;
    wire [11:0] read_addr;
    wire [15:0] safe_gain;
    wire signed [15:0] delayed_sample;
    wire signed [31:0] gain_extended;
    wire signed [31:0] echo_product;
    wire signed [31:0] echo_component;
    wire signed [32:0] sample_extended;
    wire signed [32:0] echo_extended;
    wire signed [32:0] echo_sum;

    assign safe_delay = (delay_samples == 12'd0) ? 12'd1 : delay_samples;
    // Since DEPTH is 4096, 12-bit subtraction naturally wraps modulo 4096.
    assign read_addr = write_ptr - safe_delay;
    assign safe_gain = (echo_gain_q15 > 16'd32767) ? 16'd32767 : echo_gain_q15;
    assign delayed_sample = delay_mem[read_addr];
    assign gain_extended = $signed({1'b0, safe_gain});
    assign echo_product = delayed_sample * gain_extended;
    assign echo_component = echo_product >>> 15;
    assign sample_extended = {{17{sample_in[15]}}, sample_in};
    assign echo_extended = {{1{echo_component[31]}}, echo_component};
    assign echo_sum = sample_extended + echo_extended;

    always @(posedge clk) begin
        if (rst) begin
            write_ptr <= {ADDR_WIDTH{1'b0}};
            sample_out <= 16'sd0;
            out_valid <= 1'b0;
            // Clear the memory for deterministic simulation startup.
            for (i = 0; i < DEPTH; i = i + 1)
                delay_mem[i] <= 16'sd0;
        end else begin
            out_valid <= sample_valid;
            if (sample_valid) begin
                if (echo_sum > 33'sd32767)
                    sample_out <= 16'sd32767;
                else if (echo_sum < -33'sd32768)
                    sample_out <= 16'sh8000;
                else
                    sample_out <= echo_sum[15:0];

                delay_mem[write_ptr] <= sample_in;
                write_ptr <= write_ptr + {{(ADDR_WIDTH-1){1'b0}}, 1'b1};
            end
        end
    end
endmodule
