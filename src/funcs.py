def create_script(script_dir, bench_info, dc_compile_command, clk_period):
    with open(script_dir+'/top.tcl', 'w') as f:
        print('set TOP                   '+bench_info['top'], file=f)
        print(file=f)
        print('set CONSTRAINT_VIOLATION  reports/${TOP}_vio.rpt', file=f)
        print('set TIMING_RPT            reports/${TOP}_timing.rpt', file=f)
        print('set AREA_RPT              reports/${TOP}_area.rpt', file=f)
        print('set POWER_RPT             reports/${TOP}_power.rpt', file=f)
        print('set QoR_RPT               reports/${TOP}_qor.rpt', file=f)
        print('set SAIF_RPT              reports/${TOP}_saif.rpt', file=f)
        print(file=f)
        print('set NETLIST               outputs/${TOP}_gate_v.v', file=f)
        print('set DDC                   outputs/${TOP}_ddc.ddc', file=f)
        print('set SDF                   outputs/${TOP}_sdf.sdf', file=f)
        print(file=f)
        print('read_file src/ -autoread -recursive -format verilog -top $TOP', file=f)
        print('link', file=f)
        print('uniquify', file=f)
        print('ungroup -all -flatten', file=f)
        print(file=f)
        print('set MAX_LOAD [load_of asap7sc7p5t_INVBUF_RVT_TT_ccs_211120/INVx3_ASAP7_75t_R/A]', file=f)
        print('set_load [expr $MAX_LOAD*5] [all_outputs]', file=f)
        print('set_max_area 0', file=f)
        print(file=f)
        if bench_info['type'] == 'combinational':
            print('create_clock -period ' + str(round(clk_period,2)) + ' -name VCLK', file=f)
            print('set_input_delay  0 -clock VCLK [all_inputs]', file=f)
            print('set_output_delay 0 -clock VCLK [all_outputs]', file=f)
        if bench_info['type'] == 'sequential':
            print('create_clock -name top_clk -period ' + str(round(clk_period,2)) + ' [get_ports {' + ' '.join(bench_info['clk(s)']) + '}]', file=f)
            print('set_dont_touch_network [get_ports {' + ' '.join(bench_info['clk(s)']) + '}]', file=f)
            print('set_drive 0            [get_ports {' + ' '.join(bench_info['clk(s)']) + '}]', file=f)
            print('set_ideal_network      [get_ports {' + ' '.join(bench_info['clk(s)']) + '}]', file=f)
            print('set_input_delay  0 -clock top_clk [all_inputs]', file=f)
            print('set_output_delay 0 -clock top_clk [all_outputs]', file=f)
            print(file=f)
            if 'reset(s)' in bench_info:
                print('set_dont_touch_network [get_ports {' + ' '.join(bench_info['reset(s)']) + '}]', file=f)
                print('set_drive 0            [get_ports {' + ' '.join(bench_info['reset(s)']) + '}]', file=f)
                print('set_ideal_network      [get_ports {' + ' '.join(bench_info['reset(s)']) + '}]', file=f)
                print('set_false_path -from   [get_ports {' + ' '.join(bench_info['reset(s)']) + '}]', file=f)
        print(file=f)
        print(dc_compile_command, file=f)
        print(file=f)
        # print('report_constraints  > $CONSTRAINT_VIOLATION', file=f)
        print('report_timing       > $TIMING_RPT', file=f)
        print('report_area         > $AREA_RPT', file=f)
        print('report_power        > $POWER_RPT', file=f)
        # print('report_qor          > $QoR_RPT', file=f)
        # print('report_saif         > $SAIF_RPT', file=f)
        print(file=f)
        # print('write_file -hierarchy -format verilog -output $NETLIST', file=f)
        # print('write_file -hierarchy -format ddc -output $DDC', file=f)
        # print('write_sdf $SDF', file=f)
        print(file=f)
        print('quit', file=f)



def get_PDA(module_name, rpt_dir):
    #Modified By Kxzhu
    area = 0.0
    delay = 0.0
    slack = 0.0
    power = 0.0
    with open(rpt_dir + '/' + module_name + '_area.rpt', 'r') as f:
        area_rpt = f.readlines()
        for line in area_rpt:
            if 'Total cell area' in line:
                area = float(line.split()[-1])
    with open(rpt_dir + '/' + module_name + '_timing.rpt', 'r') as f:
        delay_rpt = f.readlines()
        for line in delay_rpt:
            if 'data arrival time' in line:
                delay = float(line.split()[-1])
            if 'slack' in line:
                slack = float(line.split()[-1])
    with open(rpt_dir + '/' + module_name + '_power.rpt', 'r') as f:
        power_rpt = f.readlines()
        for line in power_rpt[-5:]:
            if 'Total' in line.split():
                power = float(line.split()[-2])
    return area, delay, slack, power