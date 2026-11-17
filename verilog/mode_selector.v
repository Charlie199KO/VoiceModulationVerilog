`timescale 1ns/1ps
// Selects one registered processing path.
// 0=bypass, 1=robot, 2=echo, 3=radio, 4=volume.
module mode_selector (
    input wire [2:0] mode,
    input wire signed [15:0] bypass_value,
    input wire signed [15:0] robot_value,
    input wire signed [15:0] echo_value,
    input wire signed [15:0] radio_value,
    input wire signed [15:0] volume_value,
    output reg signed [15:0] selected_value
);
    always @* begin
        case (mode)
            3'd0: selected_value = bypass_value;
            3'd1: selected_value = robot_value;
            3'd2: selected_value = echo_value;
            3'd3: selected_value = radio_value;
            3'd4: selected_value = volume_value;
            default: selected_value = bypass_value;
        endcase
    end
endmodule
