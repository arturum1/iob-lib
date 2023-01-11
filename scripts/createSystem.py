#!/usr/bin/env python3
import sys, os

# Add folder to path that contains python scripts to be imported
from submodule_utils import *
import ios

# Automatically include <corename>_swreg_def.vh verilog headers after PHEADER comment
def insert_header_files(template_contents, peripherals_list, submodule_dirs):
    header_index = find_idx(template_contents, "PHEADER")
    # Get each type of peripheral used
    included_peripherals = []
    for instance in peripherals_list:
        if instance['type'] not in included_peripherals:
            included_peripherals.append(instance['type'])
            # Import <corename>_setup.py module to get corename 'top'
            module = import_setup(submodule_dirs[instance['type']])
            top = module.meta['name']
            template_contents.insert(header_index, f'`include "{top}_swreg_def.vh"\n')


#Creates system based on {top}.vt template 
# setup_dir: root directory of the repository
# submodule_dirs: dictionary with directory of each submodule. Format: {"PERIPHERALCORENAME1":"PATH_TO_DIRECTORY", "PERIPHERALCORENAME2":"PATH_TO_DIRECTORY2"}
# top: top name of the system
# peripherals_list: list of dictionaries each of them describes a peripheral instance
# out_file: path to output file
# internal_wires: Optional argument. List of extra wires to create inside module
def create_systemv(setup_dir, submodule_dirs, top, peripherals_list, out_file, internal_wires=None):
    # Only create systemv if template is available
    if not os.path.isfile(setup_dir+f"/hardware/src/{top}.vt"): return

    # Read template file
    template_file = open(setup_dir+f"/hardware/src/{top}.vt", "r")
    template_contents = template_file.readlines() 
    template_file.close()

    insert_header_files(template_contents, peripherals_list, submodule_dirs)

    # Get port list, parameter list and top module name for each type of peripheral used
    port_list, params_list, top_list = get_peripherals_ports_params_top(peripherals_list, submodule_dirs)

    # Insert IOs and Instances for this type of peripheral
    for instance in peripherals_list:
        # Insert peripheral instance (in reverse order of lines)
        start_index = find_idx(template_contents, "endmodule")-1
        template_contents.insert(start_index, "      );\n")

        # Insert reserved signals
        first_reversed_signal=True
        for signal in get_reserved_signals(port_list[instance['type']]):
            template_contents.insert(start_index,"      "+
                                     get_reserved_signal_connection(signal['name'],
                                                                    top.upper()+"_"+instance['name'],
                                                                    top_list[instance['type']].upper()+"_SWREG")+",\n")
            # Remove comma at the end of last signal (first one to insert)
            if first_reversed_signal:
                template_contents[start_index]=template_contents[start_index][::-1].replace(",","",1)[::-1]
                first_reversed_signal = False

        # Insert io signals
        for signal in get_pio_signals(port_list[instance['type']]):
            template_contents.insert(start_index, '      .{}({}),\n'.format(signal['name'],ios.get_peripheral_port_mapping(instance,signal['name'])))
            # Remove comma at the end of last signal (first one to insert)
            if first_reversed_signal:
                template_contents[start_index]=template_contents[start_index][::-1].replace(",","",1)[::-1]
                first_reversed_signal = False

        # Insert peripheral instance name
        template_contents.insert(start_index, "   {} (\n".format(instance['name']))
        # Insert peripheral parameters (if any)
        if len(instance['params'])>0:
            template_contents.insert(start_index, "   )\n")
            first_reversed_signal=True
            # Insert parameters
            for param, value in instance['params'].items():
                template_contents.insert(start_index, '      .{}({}){}\n'.format(param,value,"" if first_reversed_signal else ","))
                first_reversed_signal=False
            template_contents.insert(start_index, "     #(\n")
        # Insert peripheral type
        template_contents.insert(start_index, "   {}\n".format(top_list[instance['type']]))
        template_contents.insert(start_index, "\n")
        # Insert peripheral comment
        template_contents.insert(start_index, "   // {}\n".format(instance['name']))
        template_contents.insert(start_index, "\n")

    # Insert internal module wires (if any)
    if internal_wires:
        # Find end of module header
        start_index = find_idx(template_contents, ");")
        #Insert internal wires
        for wire in internal_wires:
            template_contents.insert(start_index, f"    wire [{wire['n_bits']}-1:0] {wire['name']}\n")
        template_contents.insert(start_index, "    // Module internal wires\n")

    # Write system.v
    systemv_file = open(out_file, "w")
    systemv_file.writelines(template_contents)
    systemv_file.close()

