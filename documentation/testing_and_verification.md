# Testing and Verification

## Python tests

Run from the project root:

```powershell
python -m unittest discover -s tests -v
```

The tests cover bypass, volume scaling, echo delay startup, ring-modulator period and radio-filter output bounds.

## Verilog simulation

Install Icarus Verilog and ensure `iverilog` and `vvp` are on PATH. Generate a demo input if necessary:

```powershell
python scripts\generate_demo_wav.py
python scripts\run_verilog_demo.py --preset robot
```

The bridge compiles all Verilog modules and the file-driven testbench, writes PCM16 words as hexadecimal, invokes `vvp`, reads the output words and compares them to a Python reference.

## Expected verification

For bypass, robot, echo, radio and volume modes, Python and Verilog should match sample by sample when parameters are the same. The report includes input/output counts, mismatches, first mismatch index and maximum absolute difference.

## Long streams

The testbench streams the sample file and does not preload the whole recording into a fixed-size Verilog array. The bridge currently limits a single simulation to 2,000,000 samples to avoid accidental memory/time abuse.

## Live audio checks

The live engine reports callback overflow/underflow status, queue drops, processing errors, processed block count and last worker processing time. These are diagnostic counters, not a hard real-time guarantee.
