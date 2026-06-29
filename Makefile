NPROC      ?= $(shell nproc)
MAMBA_ENV  ?= $(HOME)/.local/share/mamba/envs/rl_zoo3

# Yosys include path — try yosys-config, fall back to system location
YOSYS_INC  := $(shell yosys-config --datdir 2>/dev/null)/include
ifeq ($(wildcard $(YOSYS_INC)/kernel/yosys.h),)
    YOSYS_INC := /usr/share/yosys/include
endif

.PHONY: all abc lsoracle abc_netlist abc_py clean

all: abc lsoracle abc_netlist abc_py

## 1. ABC with pif partitioner
abc:
	$(MAKE) -C abc_p -j$(NPROC)

## 2. LSOracle
lsoracle:
	mkdir -p LSOracle_p/build
	cd LSOracle_p/build && cmake .. \
	    -DCMAKE_BUILD_TYPE=RELEASE \
	    -DENABLE_ABC=ON \
	    -DENABLE_OPENSTA=OFF
	$(MAKE) -C LSOracle_p/build -j$(NPROC)

## 3. Yosys plugin (abc_netlist.so)
abc_netlist: abc_netlist/abc_netlist.so

abc_netlist/abc_netlist.so: abc_netlist/abc_netlist.cc
	g++ -shared -fPIC \
	    -I$(YOSYS_INC) \
	    -DYOSYS_ENABLE_ABC -DYOSYS_ENABLE_READLINE -D_YOSYS_ \
	    $< -o $@

## 4. ABC Python interface (requires rl_zoo3 conda env)
abc_py:
	@echo "Building abc_py (requires rl_zoo3 micromamba env)..."
	@if [ ! -f rl_logic_synthesis/abc_py/Makefile ]; then \
		echo "Initializing abc_py submodule..."; \
		git submodule update --init --recursive rl_logic_synthesis; \
	fi
	@if [ ! -d rl_logic_synthesis/abc_py/abc ]; then \
		echo "Cloning ABC into rl_logic_synthesis/abc_py/abc ..."; \
		git clone https://github.com/berkeley-abc/abc.git rl_logic_synthesis/abc_py/abc; \
		$(MAKE) -C rl_logic_synthesis/abc_py/abc -j$(NPROC) ABC_USE_NO_READLINE=1 ABC_USE_STDINT_H=1 ABC_USE_PIC=1 libabc.a; \
	fi
	$(MAKE) -C rl_logic_synthesis/abc_py MAMBA_ENV=$(MAMBA_ENV)

clean:
	$(MAKE) -C abc_p clean
	rm -rf LSOracle_p/build
	rm -f abc_netlist/abc_netlist.so abc_netlist/abc_netlist.d
	$(MAKE) -C rl_logic_synthesis/abc_py clean 2>/dev/null || true
