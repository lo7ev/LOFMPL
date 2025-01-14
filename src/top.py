import argparse
import subprocess
import yaml # type: ignore
import multiprocessing
from os.path import abspath, expanduser
from pathlib import Path
import time
import os

def prepare_part(partition_py, bench_info, yosys_exe, abc_exe, abc_p_exe, lsoracle_exe, part_size):
    if 'comment' not in bench_info:
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'src'])
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'scripts'])
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'reports'])
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'outputs'])
        # subprocess.run(['cp', synopsys_dc_setup_file, abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top']])
        # if 'include_dir' in bench_info:
        #     subprocess.run(['cp', '-r', abspath(expanduser(bench_info['include_dir'])), abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'src'])
        # for file in bench_info['file(s)']:
        #     subprocess.run(['cp', abspath(expanduser(file)), abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'src'])

        with open(abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/bench_info.yaml', 'w') as bench_info_f:
            yaml.dump(bench_info, bench_info_f, default_flow_style=None, sort_keys=False, width=2147483647)

        print('============= ' + bench_info['out_dir'] + ': ' + bench_info['top'] + ' =============', flush=True)
        cmd = 'python3 ' + partition_py + ' -work_dir ' +  abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + ' -yosys_exe ' + yosys_exe + ' -abc_exe ' + abc_exe + ' -abc_p_exe ' + abc_p_exe + ' -lsoracle_exe ' + lsoracle_exe + ' -part_size ' + str(part_size)
        subprocess.run(['bsub', '-R', 'rusage[mem=200000]', cmd])

def prepare_merge(merge_py, bench_info, yosys_exe, abc_exe, abc_netlist_plugin, gen_top_py, rl_yqian_P_opt_py, outputs_dir_monitor, outputs_dir_noop):
    if 'comment' not in bench_info:
        # subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'src'])
        # subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'scripts'])
        # subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'reports'])
        # subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'outputs'])
        #subprocess.run(['cp', synopsys_dc_setup_file, abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top']])
        # if 'include_dir' in bench_info:
        #     subprocess.run(['cp', '-r', abspath(expanduser(bench_info['include_dir'])), abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'src'])
        # for file in bench_info['file(s)']:
        #     subprocess.run(['cp', abspath(expanduser(file)), abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'src'])

        with open(abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/bench_info.yaml', 'w') as bench_info_f:
            yaml.dump(bench_info, bench_info_f, default_flow_style=None, sort_keys=False, width=2147483647)

        print('============= ' + bench_info['out_dir'] + ': ' + bench_info['top'] + ' =============', flush=True)
        cmd = 'python3 ' + merge_py + ' -work_dir ' +  abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + ' -yosys_exe ' + yosys_exe + ' -abc_exe ' + abc_exe + ' -abc_netlist_plugin ' + abc_netlist_plugin + ' -gen_top_py ' + gen_top_py + ' -rl_yqian_P_opt_py ' + rl_yqian_P_opt_py + ' -outputs_dir_monitor ' + outputs_dir_monitor + ' -outputs_dir_noop ' + outputs_dir_noop
        
        subprocess.run(['bsub', '-R', 'rusage[mem=200000]', cmd])
        
        time.sleep(1)

def run_rl_synthesis_workflow(benchs_info_file, rl_logic_synthesis_dir, outputs_dir_all_parts, abc_exe, process, rl_run_time, rl_run_memory):
    def get_design_dir(outputs_dir_all_parts, bench_info):
        outputs_parent_dir = str(Path(outputs_dir_all_parts).parent)
        design_dir = os.path.join(outputs_parent_dir, bench_info['out_dir'], bench_info['top'])
        return design_dir

    # Load benchmark information
    with open(benchs_info_file, 'r') as benchs_info_f:
        benchs_info = yaml.safe_load(benchs_info_f)
    
    # Iterate over each benchmark in the YAML file
    for bench_info in benchs_info:
        if 'comment' not in bench_info:
            work_dir = abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top']
            subprocess.run(['mkdir', '-p', work_dir])

            design_dir = get_design_dir(outputs_dir_all_parts, bench_info)
            for file in os.listdir(design_dir + '/src'):
                if file.endswith('.v') and file != 'top.v' and ('part_additional' not in file):
                    print(design_dir + ' ' + file)
                    params_dict = {
                        'abc_exe': abc_exe,
                        'init_bench': os.path.join(design_dir, 'src', file),
                        'step_bench': os.path.join(work_dir, file),
                        'actions': ['rewrite', 'rewrite -z', 'rewrite -l', 'rewrite -z -l', 'refactor', 'refactor -z', 'refactor -l', 'refactor -z -l', 'resub', 'resub -z', 'resub -l', 'resub -z -l', 'balance', 'fraig', '&get -n; &dsdb; &put', 'dc2'],
                        'optimize': 'mix',
                        'baseline': 'balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance',
                        'max_seq_len': 20,
                        'seq_end': 'Not_Time'
                    }
                    
                    with open(work_dir + '/' + file.replace('.v', '') + '.yml', 'w') as f:
                        yaml.dump(params_dict, f, default_flow_style=None, sort_keys=False, width=2147483647)
                    
                    print('== run_time: ', rl_run_time)
                    print('== run_memory: ', rl_run_memory / 1000, 'GB')

                    cmd = (
                        f'PYTHONPATH={rl_logic_synthesis_dir} python {rl_logic_synthesis_dir}/rl-baselines3-zoo/train.py '
                        f'--env abc-exe-opt-v0 --gym-packages gym_eda --algo ppo --log-folder {work_dir}/{file.replace(".v", "")} '
                        f'--env-kwargs \'options_yaml_file:"{work_dir}/{file.replace(".v", "")}.yml"\''
                    )

                    while True:
                        num_jobs = len(subprocess.check_output(['bjobs']).splitlines()) - 1
                        print('== process : ', process)
                        print('== run jobs: ', num_jobs)
                        if num_jobs < process:
                            subprocess.run(
                                ['bsub', '-o', f'{work_dir}/{file.replace(".v", "")}.log', '-W', str(rl_run_time), '-R', f'rusage[mem={rl_run_memory}]', cmd],
                                stdout=subprocess.DEVNULL, cwd=rl_logic_synthesis_dir
                            )
                            time.sleep(8)
                            break
                        else:
                            print('Waiting .......')
                            time.sleep(1)

def get_args():
    default = '(default: %(default)s)'
    parser = argparse.ArgumentParser()
    parser.add_argument("-partition_py", type=str, required=True, help=f"partition python file")
    parser.add_argument("-merge_py", type=str, required=True, help=f"merge python file")
    parser.add_argument("-benchs_info_file", type=str, required=True, help=f"benchmarks infomation file, YAML format")
    parser.add_argument("-yosys_exe", type=str, required=True, help=f"yosys executable file")
    parser.add_argument("-abc_exe", type=str, required=True, help=f"abc executable file")
    parser.add_argument("-abc_p_exe", type=str, required=True, help=f"abc_p executable file")
    parser.add_argument("-abc_netlist_plugin", type=str, required=True, help=f"abc netlist plugin file for yosys")
    parser.add_argument("-lsoracle_exe", type=str, required=True, help=f"lsoracle executable file")
    parser.add_argument("-part_size", type=int, default=10000, required=False, help=f"partition size, {default}")
    parser.add_argument("-process", type=int, default=1, required=False, help=f"parallel number, {default}")
    parser.add_argument("-gen_top_py", type=str, required=True, help=f"generate top module python file in lsoracle plugin")
    parser.add_argument("-rl_yqian_P_opt_py", type=str, required=True, help=f"rl_yqian_P_opt.py file")
    parser.add_argument("-outputs_dir_monitor", type=str, required=True, help=f"outputs directory with monitors")
    parser.add_argument("-outputs_dir_noop", type=str, required=True, help=f"outputs directory with noop partitions")
    parser.add_argument("-rl_logic_synthesis_dir", type=str, required=True, help=f"rl_logic_synthesis directory")
    parser.add_argument("-outputs_dir_all_parts", type=str, required=True, help=f"outputs directory conatinging all partitions")
    parser.add_argument("-rl_run_time", type=int, default=120, required=False, help=f"rl run time in minutes, {default}")
    parser.add_argument("-rl_run_memory", type=int, default=10000, required=False, help=f"rl run memory in MB, {default}")
    return parser.parse_args()


def get_design_dir(outputs_dir_all_parts, bench_info):
    outputs_parent_dir = str(Path(outputs_dir_all_parts).parent)
    design_dir = os.path.join(outputs_parent_dir, bench_info['out_dir'], bench_info['top'])
    return design_dir


def process_task(partition_py, bench_info, yosys_exe, abc_exe, abc_p_exe, lsoracle_exe, part_size,
            benchs_info_file,rl_logic_synthesis_dir,outputs_dir_all_parts,process,rl_run_time, rl_run_memory,
            merge_py, abc_netlist_plugin, gen_top_py, rl_yqian_P_opt_py, outputs_dir_monitor, outputs_dir_noop):
    if 'comment' not in bench_info:
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'src'])
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'scripts'])
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'reports'])
        subprocess.run(['mkdir', '-p', abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/' + 'outputs'])
        with open(abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + '/bench_info.yaml', 'w') as bench_info_f:
            yaml.dump(bench_info, bench_info_f, default_flow_style=None, sort_keys=False, width=2147483647)

        print('============= ' + bench_info['out_dir'] + ': ' + bench_info['top'] + ' =============', flush=True)
        work_dir = abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top']
        partition_cmd = 'python3 ' + partition_py + ' -work_dir ' +  work_dir + ' -yosys_exe ' + yosys_exe + ' -abc_exe ' + abc_exe + ' -abc_p_exe ' + abc_p_exe + ' -lsoracle_exe ' + lsoracle_exe + ' -part_size ' + str(part_size)
        subprocess.run(['bsub', '-R', 'rusage[mem=200000]', partition_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
    
        partition_done_file = os.path.join(work_dir + '/src/', 'top.outputs')
        while not os.path.exists(partition_done_file):
            print("waiting for partition  ....", flush=True)
            time.sleep(5)  
        
        print('All partition subprocesses done.', flush=True)
        #prepare_part(partition_py, bench_info, yosys_exe, abc_exe, abc_p_exe, lsoracle_exe, part_size)
        
        design_dir = get_design_dir(outputs_dir_all_parts, bench_info)
        last_file = ''
        for file in os.listdir(design_dir + '/src'):
            if file.endswith('.v') and file != 'top.v' and ('part_additional' not in file):
                print(design_dir + ' ' + file)
                params_dict = {
                    'abc_exe': abc_exe,
                    'init_bench': os.path.join(design_dir, 'src', file),
                    'step_bench': os.path.join(work_dir, file),
                    'actions': ['rewrite', 'rewrite -z', 'rewrite -l', 'rewrite -z -l', 'refactor', 'refactor -z', 'refactor -l', 'refactor -z -l', 'resub', 'resub -z', 'resub -l', 'resub -z -l', 'balance', 'fraig', '&get -n; &dsdb; &put', 'dc2'],
                    'optimize': 'mix',
                    'baseline': 'balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance',
                    'max_seq_len': 20,
                    'seq_end': 'Not_Time'
                }
                
                with open(work_dir + '/' + file.replace('.v', '') + '.yml', 'w') as f:
                    yaml.dump(params_dict, f, default_flow_style=None, sort_keys=False, width=2147483647)
                
                print('== run_time: ', rl_run_time, flush=True)
                print('== run_memory: ', rl_run_memory / 1000, 'GB', flush=True)
                opt_cmd = (
                    f'PYTHONPATH={rl_logic_synthesis_dir} python {rl_logic_synthesis_dir}/rl-baselines3-zoo/train.py '
                    f'--env abc-exe-opt-v0 --gym-packages gym_eda --algo ppo --log-folder {work_dir}/{file.replace(".v", "")} '
                    f'--env-kwargs \'options_yaml_file:"{work_dir}/{file.replace(".v", "")}.yml"\''
                )
                last_file = file.replace(".v", ".log")
                while True:
                    num_jobs = len(subprocess.check_output(['bjobs']).splitlines()) - 1
                    print('== process : ', process, flush=True)
                    print('== run jobs: ', num_jobs, flush=True)
                    if num_jobs < process:
                        subprocess.run(
                            ['bsub', '-o', f'{work_dir}/{file.replace(".v", "")}.log', '-W', str(rl_run_time), '-R', f'rusage[mem={rl_run_memory}]', opt_cmd],
                            stdout=subprocess.DEVNULL, cwd=rl_logic_synthesis_dir
                        )
                        time.sleep(8)
                        break
                    else:
                        print('Waiting .......', flush=True)
                        time.sleep(1)
                
        opt_done_file = os.path.join(work_dir, last_file)
        print(opt_done_file, flush=True)
        while not os.path.exists(opt_done_file):
            print("waiting for opt  ....", flush=True)
            time.sleep(5)  
        print('All rl_opt subprocesses done.', flush=True)
        print("=======================================================================================")
        print('Waiting for all merge subprocesses done...', flush=True)
        cmd = 'python3 ' + merge_py + ' -work_dir ' +  abspath(expanduser(bench_info['out_dir'])) + '/' + bench_info['top'] + ' -yosys_exe ' + yosys_exe + ' -abc_exe ' + abc_exe + ' -abc_netlist_plugin ' + abc_netlist_plugin + ' -gen_top_py ' + gen_top_py + ' -rl_yqian_P_opt_py ' + rl_yqian_P_opt_py + ' -outputs_dir_monitor ' + outputs_dir_monitor + ' -outputs_dir_noop ' + outputs_dir_noop
        subprocess.run(['bsub', '-R', 'rusage[mem=200000]', cmd])
        time.sleep(1)
        print('All merge subprocesses done.', flush=True)
       

if __name__ == '__main__':
    args = get_args()
    partition_py = abspath(expanduser(args.partition_py))
    merge_py = abspath(expanduser(args.merge_py))
    yosys_exe = abspath(expanduser(args.yosys_exe))
    abc_exe = abspath(expanduser(args.abc_exe))
    abc_p_exe = abspath(expanduser(args.abc_p_exe))
    lsoracle_exe = abspath(expanduser(args.lsoracle_exe))
    part_size = args.part_size    
    abc_netlist_plugin = abspath(expanduser(args.abc_netlist_plugin))
    gen_top_py = abspath(expanduser(args.gen_top_py))
    rl_yqian_P_opt_py = abspath(expanduser(args.rl_yqian_P_opt_py))
    outputs_dir_monitor = abspath(expanduser(args.outputs_dir_monitor))
    outputs_dir_noop = abspath(expanduser(args.outputs_dir_noop))
    rl_logic_synthesis_dir = abspath(expanduser(args.rl_logic_synthesis_dir))
    outputs_dir_all_parts = abspath(expanduser(args.outputs_dir_all_parts))
    process = args.process
    rl_run_time = args.rl_run_time
    rl_run_memory = args.rl_run_memory
    benchs_info_file=args.benchs_info_file

    with open(args.benchs_info_file, 'r') as benchs_info_f:
        benchs_info = yaml.safe_load(benchs_info_f)
    

    pool = multiprocessing.Pool(args.process)
    for bench_info in benchs_info:
        pool.apply_async(
            func = process_task,
            args=(partition_py, bench_info, yosys_exe, abc_exe, abc_p_exe, lsoracle_exe, part_size,
                  benchs_info_file,rl_logic_synthesis_dir,outputs_dir_all_parts,process,rl_run_time, rl_run_memory,
            merge_py, abc_netlist_plugin, gen_top_py, rl_yqian_P_opt_py, outputs_dir_monitor, outputs_dir_noop)
        )
    pool.close()
    pool.join()
