// =============================================================================
// DesignCode.v - Voice Modulator: all synthesizable design modules in one file.
// Modules: bypass, ring_modulator, echo_unit, radio_filter, volume_control, mode_selector, voice_dsp_core, top_module
// Top-level: top_module. Testbench remains in testbench/tb_audio_file.v.
// =============================================================================
`timescale 1ns/1ps

// ---------------------------- bypass.v ----------------------------
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

// ---------------------------- ring_modulator.v ----------------------------
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

// ---------------------------- echo_unit.v ----------------------------
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

// ---------------------------- radio_filter.v ----------------------------
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

// ---------------------------- volume_control.v ----------------------------
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

// ---------------------------- mode_selector.v ----------------------------
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

// ---------------------------- voice_dsp_core.v ----------------------------
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

// ---------------------------- top_module.v ----------------------------
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
