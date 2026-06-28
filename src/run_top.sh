#!/bin/bash
export PATH="$HOME/bin:$PATH"

~/.local/bin/micromamba run -n rl_zoo3 python3 ./top.py \
-partition_py ./partition.py \
-gen_top_py ./gen_top.py \
-merge_py ./merge.py \
-rl_P_opt_py ./rl_P_opt.py \
-benchs_info_file ../benchs_info/bench_info_ifft.yaml \
-yosys_exe /usr/bin/yosys \
-abc_exe ../abc_p/abc \
-abc_p_exe ../abc_p/abc \
-lsoracle_exe ../LSOracle_p/build/core/lsoracle \
-part_size 10000 \
-abc_netlist_plugin ../abc_netlist/abc_netlist.so \
-outputs_dir_monitor ../outputs \
-outputs_dir_noop ../outputs \
-rl_logic_synthesis_dir ../rl_logic_synthesis/ \
-outputs_dir_all_parts ../outputs \
-process 4
