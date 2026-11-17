`timescale 1ns/1ps
module tb_audio_file;
    reg clk = 1'b0;
    reg rst = 1'b1;
    reg sample_valid = 1'b0;
    reg signed [15:0] sample_in = 16'sd0;
    reg [2:0] mode = 3'd0;
    reg [2:0] volume_level = 3'd3;
    reg [11:0] echo_delay_samples = 12'd3200;
    reg [15:0] echo_gain_q15 = 16'd13107;
    reg [15:0] ring_half_period_samples = 16'd100;
    wire signed [15:0] sample_out;
    wire out_valid;

    reg [1023:0] input_file;
    reg [1023:0] output_file;
    integer num_samples;
    integer input_fd;
    integer output_fd;
    integer scan_result;
    integer i;
    integer processed_count;
    integer mode_arg;
    integer volume_arg;
    integer echo_delay_arg;
    integer echo_gain_arg;
    integer ring_half_arg;
    reg [15:0] input_word;

    top_module dut (
        .clk(clk), .rst(rst), .sample_valid(sample_valid),
        .sample_in(sample_in), .mode(mode), .volume_level(volume_level),
        .echo_delay_samples(echo_delay_samples), .echo_gain_q15(echo_gain_q15),
        .ring_half_period_samples(ring_half_period_samples),
        .sample_out(sample_out), .out_valid(out_valid)
    );

    always #5 clk = ~clk;

    // Observe outputs after nonblocking assignments have updated.
    always @(posedge clk) begin
        #1;
        if (!rst && out_valid) begin
            $fdisplay(output_fd, "%04h", sample_out);
            processed_count = processed_count + 1;
        end
    end

    initial begin
        input_file = "data/input_samples/input_samples.hex";
        output_file = "data/output_samples/verilog_output.hex";
        num_samples = 0;
        processed_count = 0;
        mode_arg = 0;
        volume_arg = 3;
        echo_delay_arg = 3200;
        echo_gain_arg = 13107;
        ring_half_arg = 100;

        scan_result = $value$plusargs("INPUT=%s", input_file);
        scan_result = $value$plusargs("OUTPUT=%s", output_file);
        if (!$value$plusargs("NUM=%d", num_samples)) begin
            $display("ERROR: +NUM=<sample_count> is required.");
            $finish;
        end
        scan_result = $value$plusargs("MODE=%d", mode_arg);
        scan_result = $value$plusargs("VOLUME=%d", volume_arg);
        scan_result = $value$plusargs("ECHO_DELAY=%d", echo_delay_arg);
        scan_result = $value$plusargs("ECHO_GAIN=%d", echo_gain_arg);
        scan_result = $value$plusargs("RING_HALF=%d", ring_half_arg);
        mode = mode_arg[2:0];
        volume_level = volume_arg[2:0];
        echo_delay_samples = echo_delay_arg[11:0];
        echo_gain_q15 = echo_gain_arg[15:0];
        ring_half_period_samples = ring_half_arg[15:0];

        input_fd = $fopen(input_file, "r");
        if (input_fd == 0) begin
            $display("ERROR: Could not open input file: %0s", input_file);
            $finish;
        end
        output_fd = $fopen(output_file, "w");
        if (output_fd == 0) begin
            $display("ERROR: Could not open output file: %0s", output_file);
            $fclose(input_fd);
            $finish;
        end

        repeat (4) @(negedge clk);
        rst = 1'b0;

        for (i = 0; i < num_samples; i = i + 1) begin
            scan_result = $fscanf(input_fd, "%h", input_word);
            if (scan_result != 1) begin
                $display("ERROR: Failed to read sample %0d from %0s", i, input_file);
                $fclose(input_fd);
                $fclose(output_fd);
                $finish;
            end
            @(negedge clk);
            sample_in = input_word;
            sample_valid = 1'b1;
        end

        @(negedge clk);
        sample_valid = 1'b0;
        sample_in = 16'sd0;
        $fclose(input_fd);

        wait (processed_count == num_samples);
        @(negedge clk);
        $fclose(output_fd);
        $display("SIMULATION_COMPLETE input=%0d output=%0d mode=%0d", num_samples, processed_count, mode);
        $finish;
    end

    initial begin
        #200000000;
        $display("ERROR: Simulation timeout.");
        $finish;
    end
endmodule
