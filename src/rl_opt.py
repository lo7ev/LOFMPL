#!/usr/bin/env python3
"""
RL optimization of a folder of partition .v files.

Usage:
  python3 src/rl_opt.py --input src/ --output src_opt/ [options]

Outputs one optimized .v per input partition.
Resume-safe: skips partitions whose monitor CSV already exists.
"""
import argparse, os, subprocess, shutil, re, csv, yaml
from pathlib import Path
import multiprocessing as mp

HERE   = Path(__file__).resolve().parent.parent
ABC    = HERE / 'abc_p/abc'
RL_DIR = HERE / 'rl_logic_synthesis'
TRAIN  = RL_DIR / 'rl-baselines3-zoo/train.py'

ACTIONS  = ['rewrite','rewrite -z','rewrite -l','rewrite -z -l',
            'refactor','refactor -z','refactor -l','refactor -z -l',
            'resub','resub -z','resub -l','resub -z -l',
            'balance','fraig','&get -n; &dsdb; &put','dc2']
BASELINE = ('balance; rewrite; refactor; balance; rewrite; rewrite -z; '
            'balance; refactor -z; rewrite -z; balance')


def abc(cmd):
    return subprocess.run([str(ABC), '-q', cmd], capture_output=True, text=True)

def count_nodes(v):
    for line in abc(f'read_verilog {v}; strash; print_stats').stdout.splitlines():
        if 'i/o' in line:
            m = re.search(r'and\s*=\s*(\d+)', line)
            if m: return int(m.group(1))
    return 0

def train_one(job):
    part_v, work_dir, steps, min_nodes = job
    nb = count_nodes(str(part_v))
    if nb < min_nodes:
        print(f'[skip-trivial] {part_v.stem} ({nb} nodes)', flush=True); return
    monitor = work_dir / part_v.stem / 'ppo' / 'abc-exe-opt-v0_1' / '0.monitor.csv'
    if monitor.exists():
        print(f'[skip-done]    {part_v.stem}', flush=True); return
    run_dir = work_dir / part_v.stem
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg = {'abc_exe': str(ABC), 'init_bench': str(part_v),
           'step_bench': str(run_dir / part_v.name),
           'actions': ACTIONS, 'optimize': 'area',
           'baseline': BASELINE, 'max_seq_len': 20, 'seq_end': 'Not_Time'}
    yml = run_dir / f'{part_v.stem}.yml'
    yml.write_text(yaml.dump(cfg, default_flow_style=None, sort_keys=False, width=2**31))
    env = {**os.environ, 'PYTHONPATH': str(RL_DIR)}
    subprocess.run(
        ['micromamba','run','-n','rl_zoo3','python', str(TRAIN),
         '--env','abc-exe-opt-v0','--gym-packages','gym_eda',
         '--algo','ppo','--log-folder', str(run_dir),
         '-n', str(steps), '--env-kwargs', f'options_yaml_file:"{yml}"'],
        env=env, cwd=str(RL_DIR), capture_output=True)
    print(f'[done]         {part_v.stem}', flush=True)

def apply_one(part_v, out_dir, work_dir):
    nb  = count_nodes(str(part_v))
    out = out_dir / part_v.name
    monitor = work_dir / part_v.stem / 'ppo' / 'abc-exe-opt-v0_1' / '0.monitor.csv'
    if not monitor.exists():
        shutil.copy(part_v, out); return part_v.stem, nb, nb
    rows = [r for r in csv.DictReader(l for l in open(monitor) if not l.startswith('#'))]
    if not rows:
        shutil.copy(part_v, out); return part_v.stem, nb, nb
    best = max(rows, key=lambda r: float(r.get('r', 0)))
    seq  = list(best.values())[5]
    abc(f'read_verilog {part_v}; strash; {seq}; write_verilog {out}')
    return part_v.stem, nb, count_nodes(str(out))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input',     required=True, help='folder with input partition .v files')
    ap.add_argument('--output',    required=True, help='folder for optimized .v files')
    ap.add_argument('--steps',     type=int, default=5000, metavar='N', help='PPO steps per partition [5000]')
    ap.add_argument('--workers',   type=int, default=4,    metavar='N', help='parallel training jobs [4]')
    ap.add_argument('--min-nodes', type=int, default=5,    metavar='N', help='skip partitions smaller than N nodes [5]')
    ap.add_argument('--work-dir',  default=None, metavar='DIR',
                    help='RL logs/monitors directory [<output>/.rl_work]')
    args = ap.parse_args()

    in_dir   = Path(args.input)
    out_dir  = Path(args.output);  out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(args.work_dir) if args.work_dir else out_dir / '.rl_work'
    work_dir.mkdir(parents=True, exist_ok=True)

    parts = sorted(in_dir.glob('*.v'))
    print(f'{len(parts)} partitions | {args.steps} steps | {args.workers} workers\n')

    jobs = [(p, work_dir, args.steps, args.min_nodes) for p in parts]
    with mp.Pool(args.workers) as pool:
        pool.map(train_one, jobs)

    print(f"\n{'Partition':<40} {'Before':>7} {'After':>7} {'Saved%':>7}")
    print('-' * 60)
    total_b = total_a = 0
    for p in parts:
        name, nb, na = apply_one(p, out_dir, work_dir)
        total_b += nb; total_a += na
        pct = (nb - na) / nb * 100 if nb else 0
        print(f'{name:<40} {nb:>7} {na:>7} {pct:>6.1f}%')
    pct_t = (total_b - total_a) / total_b * 100 if total_b else 0
    print('-' * 60)
    print(f'{"TOTAL":<40} {total_b:>7} {total_a:>7} {pct_t:>6.1f}%')
