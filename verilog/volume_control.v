`timescale 1ns/1ps
// Saturating PCM16 volume control.
// volume_level: 0=mute, 1=25%, 2=50%, 3=100%, 4=200%.
module volume_control (
    input wire clk,
    input wire rst,
    input wire sample_valid,
    input wire signed [15:0] sample_in,
    input wire [2:0] volume_level,
    output reg signed [15:0] sample_out,
    output reg out_valid
);
    wire signed [16:0] doubled_sample;
    assign doubled_sample = $signed({sample_in[15], sample_in}) <<< 1;

    always @(posedge clk) begin
        if (rst) begin
            sample_out <= 16'sd0;
            out_valid <= 1'b0;
        end else begin
            out_valid <= sample_valid;
            if (sample_valid) begin
                case (volume_level)
                    3'd0: sample_out <= 16'sd0;
                    3'd1: sample_out <= sample_in >>> 2;
                    3'd2: sample_out <= sample_in >>> 1;
                    3'd3: sample_out <= sample_in;
                    3'd4: begin
                        if (doubled_sample > 17'sd32767)
                            sample_out <= 16'sd32767;
                        else if (doubled_sample < -17'sd32768)
                            sample_out <= 16'sh8000;
                        else
                            sample_out <= doubled_sample[15:0];
                    end
                    default: sample_out <= sample_in;
                endcase
            end
        end
    end
endmodule
