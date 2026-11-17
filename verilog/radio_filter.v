`timescale 1ns/1ps
// First-order high-pass followed by first-order low-pass filter.
// The resulting voice band is approximately telephone/radio-like.
// Coefficients are Q1.15 values for the 16 kHz reference sample rate.
module radio_filter (
    input wire clk,
    input wire rst,
    input wire sample_valid,
    input wire signed [15:0] sample_in,
    output reg signed [15:0] sample_out,
    output reg out_valid
);
    localparam signed [15:0] ALPHA_HP_Q15 = 16'sd29126;
    localparam signed [15:0] ALPHA_LP_Q15 = 16'sd24146;

    reg signed [15:0] x_prev;
    reg signed [31:0] hp_prev;
    reg signed [31:0] lp_prev;

    wire signed [31:0] x_extended;
    wire signed [31:0] x_prev_extended;
    wire signed [31:0] hp_delta;
    wire signed [47:0] hp_delta_extended;
    wire signed [47:0] alpha_hp_extended;
    wire signed [47:0] hp_product;
    wire signed [31:0] hp_next;
    wire signed [31:0] lp_delta;
    wire signed [47:0] lp_delta_extended;
    wire signed [47:0] alpha_lp_extended;
    wire signed [47:0] lp_product;
    wire signed [31:0] lp_next;
    reg signed [15:0] clipped_output;

    assign x_extended = {{16{sample_in[15]}}, sample_in};
    assign x_prev_extended = {{16{x_prev[15]}}, x_prev};
    assign hp_delta = hp_prev + x_extended - x_prev_extended;
    // Explicitly widen both operands before multiplication so the product
    // cannot be truncated to the 32-bit input width.
    assign hp_delta_extended = {{16{hp_delta[31]}}, hp_delta};
    assign alpha_hp_extended = {{32{ALPHA_HP_Q15[15]}}, ALPHA_HP_Q15};
    assign hp_product = hp_delta_extended * alpha_hp_extended;
    assign hp_next = hp_product >>> 15;
    assign lp_delta = hp_next - lp_prev;
    assign lp_delta_extended = {{16{lp_delta[31]}}, lp_delta};
    assign alpha_lp_extended = {{32{ALPHA_LP_Q15[15]}}, ALPHA_LP_Q15};
    assign lp_product = lp_delta_extended * alpha_lp_extended;
    assign lp_next = lp_prev + (lp_product >>> 15);

    always @* begin
        if (lp_next > 32'sd32767)
            clipped_output = 16'sd32767;
        else if (lp_next < -32'sd32768)
            clipped_output = -16'sd32768;
        else
            clipped_output = lp_next[15:0];
    end

    always @(posedge clk) begin
        if (rst) begin
            x_prev <= 16'sd0;
            hp_prev <= 32'sd0;
            lp_prev <= 32'sd0;
            sample_out <= 16'sd0;
            out_valid <= 1'b0;
        end else begin
            out_valid <= sample_valid;
            if (sample_valid) begin
                x_prev <= sample_in;
                hp_prev <= hp_next;
                lp_prev <= lp_next;
                sample_out <= clipped_output;
            end
        end
    end
endmodule
