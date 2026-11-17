`timescale 1ns/1ps
// Square-carrier ring modulator.
// The carrier alternates between +1 and -1. This intentionally creates a
// buzzy/electronic effect and is simple enough for an introductory FPGA design.
module ring_modulator (
    input wire clk,
    input wire rst,
    input wire sample_valid,
    input wire signed [15:0] sample_in,
    input wire [15:0] half_period_samples,
    output reg signed [15:0] sample_out,
    output reg out_valid
);
    reg [15:0] carrier_count;
    reg carrier_positive;
    wire [15:0] safe_half_period;

    assign safe_half_period = (half_period_samples == 16'd0)
                            ? 16'd1 : half_period_samples;

    always @(posedge clk) begin
        if (rst) begin
            carrier_count <= 16'd0;
            carrier_positive <= 1'b1;
            sample_out <= 16'sd0;
            out_valid <= 1'b0;
        end else begin
            out_valid <= sample_valid;
            if (sample_valid) begin
                if (carrier_positive) begin
                    sample_out <= sample_in;
                end else if (sample_in == 16'sh8000) begin
                    // +32768 is outside signed PCM16, so saturate to +32767.
                    sample_out <= 16'sd32767;
                end else begin
                    sample_out <= -sample_in;
                end

                if (carrier_count >= (safe_half_period - 16'd1)) begin
                    carrier_count <= 16'd0;
                    carrier_positive <= ~carrier_positive;
                end else begin
                    carrier_count <= carrier_count + 16'd1;
                end
            end
        end
    end
endmodule
