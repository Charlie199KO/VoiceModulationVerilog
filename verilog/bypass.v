`timescale 1ns/1ps
module bypass (
    input wire clk,
    input wire rst,
    input wire sample_valid,
    input wire signed [15:0] sample_in,
    output reg signed [15:0] sample_out,
    output reg out_valid
);
    always @(posedge clk) begin
        if (rst) begin
            sample_out <= 16'sd0;
            out_valid <= 1'b0;
        end else begin
            out_valid <= sample_valid;
            if (sample_valid)
                sample_out <= sample_in;
        end
    end
endmodule
