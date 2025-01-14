#!/bin/bash

bsub -I 'python3 ./top.py \
-partition_py ./partition.py \
-gen_top_py ./gen_top.py \
-merge_py ./merge.py \
-rl_P_opt_py ./rl_P_opt.py \
-benchs_info_file ./benchinfo/bench_info.yaml \
-yosys_exe ../yosys/yosys \
-abc_exe ../abc_p/abc \
-abc_p_exe ../abc_p/abc \
-lsoracle_exe ../LSOracle/build/core/lsoracle \
-part_size 10000 \
-abc_netlist_plugin ../abc_netlist/abc_netlist.so \
-synopsys_dc_setup_file /home/wllpro/llwang04/zli/logic_synthesis/orig_dc/.synopsys_dc.setup \
-outputs_dir_monitor ../outputs \
-outputs_dir_noop ../outputs \
-rl_logic_synthesis_dir ../rl_logic_synthesis/ \
-outputs_dir_all_parts ../outputs \
-process 100'
