#!/bin/bash

bsub -I 'python3 ./top.py \
-partition_py ./partition.py \
-gen_top_py ./gen_top.py \
-merge_py ./merge.py \
-rl_yqian_P_opt_py ./rl_yqian_P_opt.py \
-benchs_info_file ./benchinfo/bench_info.yaml \
-yosys_exe /home/wllpro/llwang04/yosys-yosys-0.32/yosys \
-abc_exe /home/wllpro/llwang04/abc-master/abc \
-abc_p_exe /home/wllpro/llwang04/zli/logic_synthesis/partition_adaptive_mffc_kahypar_n10000/abc_p/abc \
-lsoracle_exe /home/wllpro/llwang04/zli/logic_synthesis/partition_adaptive_mffc_kahypar_n10000/LSOracle/build/core/lsoracle \
-part_size 10000 \
-abc_netlist_plugin /home/wllpro/llwang04/zli/logic_synthesis/partition_n10000_rl_yqian_merge/abc_netlist/abc_netlist.so \
-synopsys_dc_setup_file /home/wllpro/llwang04/zli/logic_synthesis/orig_dc/.synopsys_dc.setup \
-outputs_dir_monitor /home/wllpro/llwang05/zli/logic_synthesis/partition_n10000_rl_yqian_opt/outputs \
-outputs_dir_noop /home/wllpro/llwang05/zli/logic_synthesis/partition_n10000/outputs \
-rl_logic_synthesis_dir /home/wllpro/llwang04/zli/logic_synthesis/rl_yqian_P_opt/rl_logic_synthesis/ \
-outputs_dir_all_parts ./outputs \
-process 100'
