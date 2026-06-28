# LOFMPL Build Guide

Complete step-by-step instructions to build LOFMPL from scratch on an Arch-based Linux system (CachyOS, Arch, Manjaro, etc.). Adapt package names for Debian/Ubuntu as noted.

---

## Prerequisites (install manually)

### System packages

**Arch / CachyOS:**
```bash
sudo pacman -S --needed \
  git cmake make gcc g++ python3 python-pip \
  yosys \
  boost boost-libs \
  tcl \
  readline zlib curl wget \
  swig
```

**Debian / Ubuntu equivalent:**
```bash
sudo apt install -y \
  git cmake make g++ python3 python3-pip \
  yosys \
  libboost-all-dev \
  tcl-dev \
  libreadline-dev zlib1g-dev curl wget \
  swig
```

### micromamba (Python environment manager — no root needed)

```bash
mkdir -p ~/.local/bin
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C ~/.local/bin bin/micromamba --strip-components=1
# Add to your shell config (~/.bashrc or ~/.zshrc or ~/.config/fish/config.fish):
export PATH="$HOME/.local/bin:$PATH"
```

### fake bsub / bjobs (replaces LSF HPC scheduler)

```bash
mkdir -p ~/bin

cat > ~/bin/bsub << 'EOF'
#!/bin/bash
BSUB_JOBS_DIR="${HOME}/.bsub_jobs"
mkdir -p "$BSUB_JOBS_DIR"
LOG_FILE=""; CMD=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o) LOG_FILE="$2"; shift 2 ;;
        -W|-R|-J|-q|-n|-M|-u|-P|-G|-sp|-m) shift 2 ;;
        -I|-r|-K) shift ;;
        -*) shift ;;
        *) CMD="$1"; shift ;;
    esac
done
[ -z "$CMD" ] && exit 0
if [ -n "$LOG_FILE" ]; then
    bash -c "$CMD" > "$LOG_FILE" 2>&1 &
else
    bash -c "$CMD" &
fi
PID=$!
echo "$PID" > "$BSUB_JOBS_DIR/${PID}.pid"
echo "Job <$PID> is submitted to queue <normal>"
EOF

cat > ~/bin/bjobs << 'EOF'
#!/bin/bash
BSUB_JOBS_DIR="${HOME}/.bsub_jobs"
mkdir -p "$BSUB_JOBS_DIR"
RUNNING=0
for pid_file in "$BSUB_JOBS_DIR"/*.pid 2>/dev/null; do
    [ -f "$pid_file" ] || continue
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        RUNNING=$((RUNNING + 1))
    else
        rm -f "$pid_file"
    fi
done
if [ "$RUNNING" -eq 0 ]; then
    echo "No unfinished job found"
else
    echo "JOBID   USER    STAT  QUEUE      FROM_HOST   EXEC_HOST   JOB_NAME   SUBMIT_TIME"
    for pid_file in "$BSUB_JOBS_DIR"/*.pid 2>/dev/null; do
        [ -f "$pid_file" ] || continue
        pid=$(cat "$pid_file")
        kill -0 "$pid" 2>/dev/null && echo "$pid  $(whoami)  RUN   normal  localhost  localhost  job  $(date '+%b %d %H:%M')"
    done
fi
EOF

chmod +x ~/bin/bsub ~/bin/bjobs
export PATH="$HOME/bin:$PATH"   # also add this to your shell config
```

---

## Step 1 — Clone LOFMPL

```bash
git clone https://github.com/kxzhu0505/LOFMPL.git
cd LOFMPL
git submodule update --init --recursive
```

---

## Step 2 — Build ABC (`abc_p`)

```bash
cd abc_p
make -j$(nproc)
cd ..
```

---

## Step 3 — Build LSOracle (`LSOracle_p`)

> Note: build with `ENABLE_OPENSTA=OFF` — the OpenSTA SWIG wrapper is incompatible with GCC 15+/16+.

```bash
cd LSOracle_p
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RELEASE -DENABLE_ABC=ON -DENABLE_OPENSTA=OFF
make -j$(nproc)
cd ../..
```

---

## Step 4 — Build `abc_netlist.so`

> Requires system yosys headers. `yosys-config` must be on PATH.

The upstream `abc_netlist.cc` has a type error for Yosys ≥ 0.45 — `log_signal()` now returns `std::string` but is passed to `strlen()`. Patch it:

```bash
cd abc_netlist
sed -i 's/int(strlen(log_signal(\(.*\)))/int(std::string(log_signal(\1)).size()/' abc_netlist.cc
g++ -shared -fPIC -o abc_netlist.so abc_netlist.cc $(yosys-config --cxxflags --ldflags)
cd ..
```

---

## Step 5 — Set up RL environment

### 5a. Create Python 3.9 environment

```bash
micromamba create -n rl_zoo3 python=3.9 boost -c conda-forge -y
```

### 5b. Clone and patch rl-baselines3-zoo

```bash
cd rl_logic_synthesis
git clone --depth=1 --branch v1.5.0 https://github.com/DLR-RM/rl-baselines3-zoo.git
cp utils/exp_manager.py rl-baselines3-zoo/utils/exp_manager.py
```

> The bundled `exp_manager.py` fixes a SkoptSampler import error introduced in optuna 4.x (the class moved from `optuna.integration.skopt` to `optuna_integration`).

### 5c. Install Python packages

```bash
mkdir -p ~/.pip_tmp

# Install CPU-only PyTorch first (avoids filling /tmp with CUDA packages)
TMPDIR=~/.pip_tmp micromamba run -n rl_zoo3 pip install \
  torch --index-url https://download.pytorch.org/whl/cpu

# gym 0.21.0 has an invalid version specifier in setup.py — patch and install from source
cd ~/.pip_tmp
micromamba run -n rl_zoo3 pip download "gym==0.21.0" --no-deps
tar -xzf gym-0.21.0.tar.gz
sed -i 's/"opencv-python>=3\."/"opencv-python>=3"/' gym-0.21.0/setup.py
TMPDIR=~/.pip_tmp micromamba run -n rl_zoo3 pip install ./gym-0.21.0/ --no-deps
cd -

# Install SB3 — MUST be 1.8.0; versions 2.x require gymnasium and break with gym 0.21
TMPDIR=~/.pip_tmp micromamba run -n rl_zoo3 pip install \
  "stable-baselines3==1.8.0" \
  "sb3-contrib==1.8.0" \
  "scikit-optimize" "optuna" "pytablewriter" "seaborn" \
  "cloudpickle>=1.5.0" "plotly" "rliable>=1.0.5" "wandb" dgl

# Fix DGL 2.1.0 incompatibility with torchdata 0.11+ (missing datapipes/distributed)
SITE=$(micromamba run -n rl_zoo3 python -c "import site; print(site.getsitepackages()[0])")

mkdir -p $SITE/torchdata/datapipes/iter $SITE/torchdata/dataloader2
touch $SITE/torchdata/datapipes/__init__.py $SITE/torchdata/dataloader2/__init__.py
printf 'class IterDataPipe:\n    pass\n' > $SITE/torchdata/datapipes/iter/__init__.py
touch $SITE/torchdata/dataloader2/graph.py

micromamba run -n rl_zoo3 python3 - <<'PYEOF'
import re, pathlib, site
s = pathlib.Path(site.getsitepackages()[0])

f = s / "dgl/__init__.py"
t = f.read_text()
t = t.replace(
    'from . import distributed',
    'try:\n        from . import distributed\n    except Exception:\n        pass'
)
f.write_text(t)

f = s / "dgl/dataloading/__init__.py"
t = f.read_text()
t = t.replace(
    '    from .dist_dataloader import *',
    '    try:\n        from .dist_dataloader import *\n    except Exception:\n        pass'
)
f.write_text(t)
PYEOF

cd ..  # back to LOFMPL root
```

### 5d. Build `abc_py` Python module

```bash
cd rl_logic_synthesis
git clone --depth=1 https://github.com/phyzhenli/abc_py.git
cd abc_py
git clone --depth=1 https://github.com/berkeley-abc/abc.git
make -j$(nproc) -C abc ABC_USE_NO_READLINE=1 ABC_USE_STDINT_H=1 ABC_USE_PIC=1 libabc.a

# Patch Makefile for Python 3.9 + micromamba boost
MAMBA_ENV="$HOME/.local/share/mamba/envs/rl_zoo3"
cat > Makefile << MKEOF
CC = g++
CFLAGS = -std=c++11 -DABC_USE_STDINT_H=1 -fPIC
ABC_DIR = ./abc
ABC_INC = -I\$(ABC_DIR)/src
ABC_LIB = -L\$(ABC_DIR) -labc
PYTHON_VER = 3.9
MAMBA_ENV = ${MAMBA_ENV}
PYTHON_INC = -I\$(MAMBA_ENV)/include/python\$(PYTHON_VER)
PYTHON_LIB = -L\$(MAMBA_ENV)/lib -lpython\$(PYTHON_VER)
BOOST_DIR  = \$(MAMBA_ENV)
BOOST_INC  = -I\$(BOOST_DIR)/include
BOOST_LIBS = -L\$(BOOST_DIR)/lib -lboost_python39 -lboost_numpy39
TARGET = abc_py_.so
SRC = abc_py_.cpp
OBJS = \$(SRC:.cpp=.o)
ALL: \$(TARGET)
\$(TARGET): \$(OBJS)
	\$(CC) -shared -Wl,--export-dynamic \$^ \$(ABC_LIB) \$(PYTHON_LIB) \$(BOOST_LIBS) -o \$@
.PHONY:clean
clean:
	rm -rf \$(TARGET) \$(OBJS)
%.o:%.cpp
	\$(CC) \$(CFLAGS) \$(ABC_INC) \$(BOOST_INC) \$(PYTHON_INC) -o \$@ -c \$<
MKEOF

micromamba run -n rl_zoo3 make
cd ../..
```

> **Tab warning:** if you copy-pasted this block from a browser rather than running it as a script, the Makefile recipe lines may have spaces instead of tabs. Fix with: `sed -i 's/^    /\t/' Makefile` before running make.

### 5e. Install pybind11

```bash
micromamba run -n rl_zoo3 pip install pybind11
```

### 5f. Patch gym_eda and abc_exe

The `gym_eda` package has two bugs that must be fixed manually.

**Fix 1 — `gym_eda/__init__.py`**: The upstream file tries to import `cirkit_py`, `imap`, and ASIC environments that are not installed. These imports crash the entire gym registration on `import gym_eda`. Replace the broken import block:

```bash
cat > rl_logic_synthesis/gym_eda/__init__.py << 'EOF'
from gym_eda.abc_exe import AbcExeOpt

from gym.envs.registration import register

register(
    id='abc-v0',
    entry_point='gym_eda:AbcEnv',
)

register(
    id='abc-exe-opt-v0',
    entry_point='gym_eda:AbcExeOpt',
)
EOF
```

**Fix 2 — `rl_logic_synthesis/gym_eda/abc_exe.py`**: The three `getStats` methods (`getInitStats`, `getBaseStats`, `getStepStats`) leave `nd` and `lev` undefined if ABC's `print_stats` output has no `i/o` line — which happens when an optimizer eliminates all AND gates. Add defaults before the parse loop in each function:

```bash
python3 - <<'PYEOF'
import re, pathlib

f = pathlib.Path("rl_logic_synthesis/gym_eda/abc_exe.py")
t = f.read_text()

# Insert 'nd, lev = 0, 0' before every 'for line in abc_log' loop in the three stat functions
t = re.sub(
    r'(abc_log = subp_log\.stdout[^\n]+\n)(\s+for line in abc_log)',
    r'\1        nd, lev = 0, 0\n\2',
    t
)
f.write_text(t)
print("Patched", t.count("nd, lev = 0, 0"), "occurrences")
PYEOF
```

### 5g. Add `abc-exe-opt-v0` hyperparameters to ppo.yml

The rl-baselines3-zoo v1.5.0 does not include hyperparameters for `abc-exe-opt-v0`. Append them:

```bash
cat >> rl_logic_synthesis/rl-baselines3-zoo/hyperparams/ppo.yml << 'EOF'

abc-exe-opt-v0:
  n_envs: 1
  n_timesteps: !!float 2e5
  policy: 'MlpPolicy'
  n_steps: 100
  n_epochs: 20
  learning_rate: !!float 1e-3
  clip_range: 0.2
  gae_lambda: 0.95
  gamma: 0.99
  ent_coef: 0.01
  vf_coef: 0.5
  batch_size: 100
EOF
```

---

## Step 6 — Verify

```bash
micromamba run -n rl_zoo3 python -c "
import gym, stable_baselines3, sb3_contrib, dgl, torch
print('gym:', gym.__version__)               # must be 0.21.0
print('stable-baselines3:', stable_baselines3.__version__)  # must be 1.8.0
print('dgl:', dgl.__version__)
print('torch:', torch.__version__)
print('OK')
"
ls abc_p/abc LSOracle_p/build/core/lsoracle abc_netlist/abc_netlist.so rl_logic_synthesis/abc_py/abc_py_.so
```

---

## Using LOFMPL

### Pipeline overview

```
Verilog RTL
    │
    ▼  partition.py
    │  Yosys: flatten/proc/techmap → abc.aig (sequential AIGER)
    │  abc_p pif: partition AIG into network_*.v (combinational slices)
    │  LSOracle oracle: re-partition any oversized parts
    │
    ▼  [optional] RL optimization (top.py / rl-baselines3-zoo)
    │  PPO trains on each partition, finds best rewrite sequence
    │
    ▼  merge.py
    │  rl_P_opt.py: applies best RL sequences via ABC (or copies noop if no RL)
    │  gen_top.py: builds flat netlist.v wrapper over all partitions
    │  Yosys abc_netlist plugin: CEC vs original RTL, tech-map → output.v
    │
    ▼  output.v  (sequential design with registers restored, tech-mapped)
```

**Why partitions are combinational:** ABC represents flip-flops as AIG latches (current state = extra PI, next state = extra PO). `abc_p pif` partitions only the combinational logic between register stages. The original register structure is reconstructed during the merge step via the `abc_netlist` Yosys plugin, which CEC-verifies the optimized combinational logic against the original RTL and remaps.

---

### Benchmark YAML

Create `benchs_info/my_bench.yaml`:

```yaml
- file(s): [path/to/design.v, path/to/submodule.v]
  top: top_module_name
  out_dir: ./outputs/my_design        # relative to LOFMPL root
  type: combinational                  # or sequential
```

Add `comment: skip` to any entry to exclude it from a run.

---

### Basic case: partition + reassemble (no RL)

This produces a functionally equivalent output with the original register structure restored but without RL-based combinational optimization.

All commands run from the **LOFMPL root** (not from `src/`).

```bash
DESIGN=my_design
TOP=top_module_name
WORK=./outputs/${DESIGN}/${TOP}

# 1. Create output directory tree and bench_info.yaml
mkdir -p ${WORK}/src ${WORK}/scripts ${WORK}/reports ${WORK}/outputs
cat > ${WORK}/bench_info.yaml << 'EOF'
file(s): [path/to/design.v]
top: top_module_name
out_dir: ./outputs/my_design
type: combinational
EOF

# 2. Partition: Yosys → AIG → abc_p pif → LSOracle re-partition large parts
#    Produces: ${WORK}/src/network_*.v, network_*.ports, top.inputs, top.outputs
python3 src/partition.py \
  -work_dir ${WORK} \
  -yosys_exe /usr/bin/yosys \
  -abc_exe ./abc_p/abc \
  -abc_p_exe ./abc_p/abc \
  -lsoracle_exe ./LSOracle_p/build/core/lsoracle \
  -part_size 10000

# 3. Generate top-level wrapper over all partitions
#    Produces: ${WORK}/src/netlist.v
python3 src/gen_top.py -dir ${WORK}/src -module_name netlist

# 4. Flatten all partitions into a single combinational netlist
#    Produces: ${WORK}/netlist.v
yosys -Q -T -p "
  read_verilog ${WORK}/src/*.v;
  hierarchy -top netlist;
  flatten; techmap; opt -purge;
  write_verilog -noattr ${WORK}/netlist.v
"

# 5. Archive partition sources
mv ${WORK}/src/* ${WORK}/outputs/

# 6. CEC vs original RTL + technology mapping — restores registers
#    Produces: ${WORK}/src/output.v  (final sequential, tech-mapped design)
yosys -Q -T -m ./abc_netlist/abc_netlist.so -p "
  read_verilog -nolatches path/to/design.v;
  hierarchy -check -top ${TOP};
  flatten; proc; opt -purge; memory; opt -purge; fsm; opt -purge; techmap; opt -purge;
  abc_netlist -netlist ${WORK}/netlist.v -script '+cec ${WORK}/netlist.v; quit';
  opt -purge;
  write_verilog -noattr ${WORK}/src/output.v
"
```

Final result: `${WORK}/src/output.v` — original RTL with registers, optimized combinational logic, mapped to `lib/asap7.lib`.

---

### Full pipeline: partition + RL optimization + reassemble

The full pipeline trains PPO on every partition in parallel, then applies the best discovered rewrite sequence before reassembling.

#### 1. Edit `src/run_top.sh`

Key fields to configure:

```bash
-benchs_info_file ../benchs_info/my_bench.yaml   # your benchmark YAML
-part_size        10000                            # max AIG nodes per partition
-process          4                                # max parallel RL jobs
```

All paths in the provided `run_top.sh` already point to the correct binaries (`/usr/bin/yosys`, `abc_p/abc`, `LSOracle_p/build/core/lsoracle`, `abc_netlist/abc_netlist.so`).

#### 2. Run

```bash
cd src
bash run_top.sh
```

> `run_top.sh` already exports `PATH` (for bsub/bjobs) and calls `micromamba run -n rl_zoo3` internally — do not wrap it in `micromamba run` again.

`top.py` runs these stages in sequence per benchmark:

| Stage | Script | Output |
|-------|--------|--------|
| Partition | `partition.py` | `<out_dir>/<top>/src/network_*.v` |
| RL train | `rl-baselines3-zoo/train.py` (PPO) | `<out_dir>/<top>/<part>/ppo/.../0.monitor.csv` |
| Select best | `rl_P_opt.py` | optimized `src/*.v` |
| Assemble | `gen_top.py` + Yosys | `src/netlist.v` → flat `netlist.v` |
| Tech map | `abc_netlist.so` (CEC) | `src/output.v` |

Progress is printed to stdout as stages complete. RL training time is controlled by `-rl_run_time` (minutes, default 120).

#### 3. Monitor progress

```bash
# Check how many RL jobs are still running
bjobs

# Watch log for a specific partition
tail -f outputs/my_design/top_module/network_0/ppo/abc-exe-opt-v0_1/0.monitor.csv
```

#### 4. Run merge manually (after RL is done)

If you want to run just the reassembly step (e.g. RL already completed):

Run from the **LOFMPL root** (not from `src/`):

```bash
~/.local/bin/micromamba run -n rl_zoo3 python3 src/merge.py \
  -work_dir outputs/my_design/top_module \
  -yosys_exe /usr/bin/yosys \
  -abc_exe abc_p/abc \
  -abc_netlist_plugin abc_netlist/abc_netlist.so \
  -gen_top_py src/gen_top.py \
  -rl_P_opt_py src/rl_P_opt.py \
  -outputs_dir_monitor outputs \
  -outputs_dir_noop outputs
```

---

## Known Issues & Workarounds

| Issue | Fix |
|-------|-----|
| `LSOracle_p` OpenSTA build fails (SWIG + GCC 15+) | Use `-DENABLE_OPENSTA=OFF` |
| `abc_netlist.cc` type error with Yosys ≥ 0.45 | Patch `strlen(log_signal(...))` → `std::string(log_signal(...)).size()` |
| `gym==0.21` invalid metadata (`opencv-python>=3.`) | Download source, patch `setup.py`, install manually (Step 5c) |
| DGL 2.1.0 fails to import (`torchdata.datapipes` removed) | Stub missing modules + wrap `dgl.distributed` import in try/except (Step 5c) |
| `/tmp` too small for CUDA PyTorch download | Install CPU-only torch with `TMPDIR=~/.pip_tmp` |
| `stable-baselines3` 2.x incompatible with `gym` 0.21 | Pin to `==1.8.0` — SB3 2.x switched to `gymnasium` API (Step 5c) |
| `gym_eda` crashes on import (`cirkit_py` not installed) | Replace `__init__.py` with only the `abc-exe-opt-v0` registration (Step 5f) |
| `UnboundLocalError: nd referenced before assignment` in `abc_exe.py` | Add `nd, lev = 0, 0` defaults before parse loop in all three stat methods (Step 5f) |
| `KeyError` for `abc-exe-opt-v0` in `ppo.yml` | Append hyperparameter block to `ppo.yml` (Step 5g) |
| `optuna.integration.skopt.SkoptSampler` missing (optuna 4.x) | Handled by the patched `exp_manager.py` copy in Step 5b |
| `yosys` not found (relative path in partition.py) | Pass `/usr/bin/yosys` instead of `yosys` |
| `bsub`/`bjobs` not available (no LSF cluster) | Use fake wrappers from Prerequisites section |
| `partition.py` fails with `ERROR: Can't open ABC output file` | System Yosys ≥ 0.60 changed how `abc -nocleanup -script` writes temp files. Workaround: skip `partition.py` and run `abc_p pif` directly: `echo "read_aiger design.aig; pif -d ${WORK}/src/" \| abc_p/abc`, then generate `.ports` files manually with `gen_ports.py` or by parsing the module header. |
| `abc_py` Makefile tabs lost when copy-pasting from rendered markdown | Makefile recipe lines require a real tab character, not spaces. If you copy-pasted from a browser, run `sed -i 's/^    /\t/' Makefile` inside `rl_logic_synthesis/abc_py/` to fix indentation, then re-run `micromamba run -n rl_zoo3 make`. |
