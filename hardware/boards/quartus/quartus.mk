ifeq ($(IS_FPGA),1)
FPGA_OBJ:=$(NAME).sof
else
FPGA_OBJ:=$(NAME).qxp
endif

FPGA_TEX:=quartus.tex
FPGA_SERVER=$(QUARTUS_SERVER)
FPGA_USER=$(QUARTUS_USER)
FPGA_ENV=$(QUARTUSPATH)/nios2eds/nios2_command_shell.sh

$(FPGA_OBJ): $(VHDR) $(VSRC) $(wildcard *.sdc)
	$(FPGA_ENV) quartus_sh -t fpga_tool.tcl $(NAME) $(TOP_MODULE) "$(VSRC)" $(FPGA_PART) $(IS_FPGA)
	LOG=output_files/*.fit.summary ../../sw/bash/quartus2tex.sh

