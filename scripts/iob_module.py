import os
import shutil
import sys
import importlib

import iob_colors
import if_gen
from mk_configuration import config_build_mk
import build_srcs
import verilog_tools
import mkregs
import blocks
import ios
import mk_configuration as mk_conf


class iob_module:
    """Generic class to describe a base iob-module"""

    ###############################################################
    # IOb module attributes: common to all iob-modules (subclasses)
    ###############################################################

    # Standard attributes common to all iob-modules
    name = "iob_module"  # Verilog module name (not instance name)
    csr_if = "iob"
    version = "1.0"  # Module version
    previous_version = None  # Module version
    flows = ""  # Flows supported by this module
    setup_dir = ""  # Setup directory for this module
    build_dir = ""  # Build directory for this module
    confs = None  # List of configuration macros/parameters for this module
    regs = None  # List of registers for this module
    ios = None  # List of I/O for this module
    block_groups = None  # List of block groups for this module. Used for documentation.
    wire_list = None  # List of internal wires of the Verilog module. Used to interconnect module components.
    is_top_module = False  # Select if this module is the top module

    _initialized_attributes = (
        False  # Store if attributes have been initialized for this class
    )

    submodule_list = None  # List of submodules to setup

    # List of setup purposes for this module. Also used to check if module has already been setup.
    _setup_purpose = None

    # Dictionary of headers generated by the `generate` method, and their purpose.
    __generated_headers = {}

    # Read-only dictionary with relation between the setup_purpose and the corresponding source folder
    PURPOSE_DIRS = {
        "hardware": "hardware/src",
        "simulation": "hardware/simulation/src",
        "fpga": "hardware/fpga/src",
    }

    def __init__(
        self,
        name="",
        description="default description",
        parameters={},
    ):
        """Constructor to build verilog instances.
        :param str name: Verilog instance name
        :param str description: Verilog instance description
        :param dict parameters: Verilog parameters
        """
        if not name:
            name = f"{self.name}_0"
        self.name = name
        self.description = description
        self.parameters = parameters

    ###############################################################
    # Methods NOT to be overriden by subclasses
    ###############################################################

    @staticmethod
    def find_modules(search_path="."):
        """Run a BFS for python modules under the given directory and append their paths to `sys.path`.
        This allows every module found to be imported.
        :param str search_path: Path to search for modules
        """
        dirs = [search_path]
        found_modules = []
        return_values = []
        # while there are dirs to search
        while len(dirs):
            nextDirs = []
            for parent in dirs:
                # Scan this dir
                for f in os.listdir(parent):
                    # if there is a dir, then save for next ittr
                    ff = os.path.join(parent, f)
                    if os.path.isdir(ff):
                        nextDirs.append(ff)
                        continue
                    # if there is a python module and has not been added before, then add it to sys.path
                    if f.endswith(".py") and f not in found_modules:
                        sys.path.append(parent)
                        found_modules.append(f)
            # once we've done all the current dirs then
            # we set up the next itter as the child dirs
            # from the current itter.
            dirs = nextDirs

    @classmethod
    def setup_as_top_module(cls):
        """Initialize the setup process for the top module.
        This method should only be called once, and only for the top module class.
        It is typically called by the `bootstrap.py` script.
        """
        cls.__setup(is_top_module=True)

    @classmethod
    def __setup(cls, purpose="hardware", is_top_module=False):
        """Private setup method for this module.
        purpose: Reason for setting up the module. Used to select between the standard destination locations.
        is_top_module: Select if this is the top module. This should only be enabled on the top module class.
        """
        # print(f'DEBUG: Setup: {cls.name}, purpose: {purpose}') # DEBUG

        # Initialize empty list for purpose
        if cls._setup_purpose == None:
            cls._setup_purpose = []

        # Don't setup if module has already been setup for this purpose or for the "hardware" purpose.
        if purpose in cls._setup_purpose or "hardware" in cls._setup_purpose:
            return

        # Only init attributes if this is the first time we run setup
        if not cls._setup_purpose:
            cls.is_top_module = is_top_module
            cls.init_attributes()

        # Create build directory this is the top module class, and is the first time setup
        if is_top_module and not cls._setup_purpose:
            cls.__create_build_dir()

        # Add current setup purpose to list
        cls._setup_purpose.append(purpose)

        cls._specific_setup()
        cls._post_setup()

    @classmethod
    def init_attributes(cls):
        """Public method to initialize attributes of the class
        This method is automatically called by the `setup` method.
        """
        # Only run this method if attributes have not yet been initialized
        if cls._initialized_attributes:
            return
        cls._initialized_attributes = True

        # Set the build directory in the `iob_module` superclass, so everyone has access to it
        if cls.is_top_module:
            # Auto-fill build directory if its not set
            if not cls.build_dir:
                iob_module.build_dir = f"../{cls.name}_{cls.version}"
            else:
                iob_module.build_dir = cls.build_dir

        # Copy build directory from the `iob_module` superclass
        cls.build_dir = iob_module.build_dir

        # Copy current version to previous version if it is not set
        if not cls.previous_version:
            cls.previous_version = cls.version

        # Initialize empty lists for attributes (We can't initialize in the attribute declaration because it would cause every subclass to reference the same list)
        cls.confs = []
        cls.regs = []
        cls.ios = []
        cls.block_groups = []
        cls.submodule_list = []
        cls.wire_list = []

        cls._init_attributes()

        cls._create_submodules_list()

        # Call _setup_* function for attributes (these may be overriden by subclasses)
        cls._setup_confs()
        cls._setup_ios()
        cls._setup_regs()

    @classmethod
    def _specific_setup(cls):
        """Private method to setup and instantiate submodules before specific setup"""
        # Setup submodules placed in `submodule_list` list
        cls._setup_submodules(cls.submodule_list)
        # Create instances of submodules (previously setup)
        cls._create_instances()
        # Setup block groups (not called from init_attributes() because
        # this function has instances of modules that are only created by this function)
        cls._setup_block_groups()
        
    ###############################################################
    # Methods commonly overriden by subclasses
    ###############################################################

    @classmethod
    def _init_attributes(cls):
        """Default method to init attributes does nothing"""
        pass

    @classmethod
    def _create_submodules_list(cls, submodule_list=[]):
        cls.submodule_list += submodule_list

    @classmethod
    def _create_instances(cls):
        """Default method to instantiate modules does nothing"""
        pass

    @classmethod
    def _setup_confs(cls, confs=[]):
        cls.update_dict_list(cls.confs, confs)

    @classmethod
    def _setup_ios(cls, ios=[]):
        cls.update_dict_list(cls.ios, ios)

    @classmethod
    def _setup_regs(cls, regs=[]):
        cls.update_dict_list(cls.regs, regs)

    @classmethod
    def _setup_block_groups(cls, block_groups=[]):
        cls.update_dict_list(cls.block_groups, block_groups)

    ###############################################################
    # Methods optionally overriden by subclasses
    ###############################################################

    @classmethod
    def _post_setup(cls):
        """Launch post(-specific)-setup tasks"""
        # Setup flows (copy LIB files)
        build_srcs.flows_setup(cls)

        # Copy sources from the module's setup dir (and from its superclasses)
        cls._copy_srcs()

        # Auto-add common module macros and submodules
        cls._auto_add_settings()

        # Generate hw, sw and doc files
        cls._generate_files()

        # Run `*_setup.py` python scripts
        cls._run_setup_files()

        if cls.is_top_module:
            # Replace Verilog snippet includes
            cls._replace_snippet_includes()
            # Clean duplicate sources in `hardware/src` and its subfolders (like `hardware/simulation/src`)
            cls._remove_duplicate_sources()

    @classmethod
    def _generate_files(cls):
        """Generate hw, sw and doc files"""
        mkregs_obj, reg_table = cls._build_regs_table()
        cls._generate_hw(mkregs_obj, reg_table)
        cls._generate_sw(mkregs_obj, reg_table)
        cls._generate_doc(mkregs_obj, reg_table)

    @classmethod
    def _auto_add_settings(cls):
        """Auto-add settings like macros and submodules to the module"""
        # Auto-add 'VERSION' macro if it doesn't exist.
        # But only if this module has at least one other configuration aswell
        # (to prevent lots of LIB modules with only the `VERSION` macron)
        if cls.confs:
            for macro in cls.confs:
                if macro["name"] == "VERSION":
                    break
            else:
                cls.confs.append(
                    {
                        "name": "VERSION",
                        "type": "M",
                        "val": "16'h" + build_srcs.version_str_to_digits(cls.version),
                        "min": "NA",
                        "max": "NA",
                        "descr": "Product version. This 16-bit macro uses nibbles to represent decimal numbers using their binary values. The two most significant nibbles represent the integral part of the version, and the two least significant nibbles represent the decimal part. For example V12.34 is represented by 0x1234.",
                    }
                )
        if cls.regs:
            # Auto-add iob_ctls module
            if cls.name != "iob_ctls":
                from iob_ctls import iob_ctls

                iob_ctls.__setup(purpose=cls.get_setup_purpose())
            ## Auto-add iob_s_port.vh
            cls.__generate({"interface": "iob_s_port"}, purpose=cls.get_setup_purpose())
            ## Auto-add iob_s_portmap.vh
            cls.__generate(
                {"interface": "iob_s_s_portmap"}, purpose=cls.get_setup_purpose()
            )

    @classmethod
    def _build_regs_table(cls, no_overlap=False):
        """Build registers table.
        :returns mkregs mkregs_obj: Instance of mkregs class
        :returns list reg_table: Register table generated by `get_reg_table` method of `mkregs_obj`
        """
        # Don't create regs table if module does not have regs
        if not cls.regs:
            return None, None

        # Make sure 'general' registers table exists
        general_regs_table = next((i for i in cls.regs if i["name"] == "general"), None)
        if not general_regs_table:
            general_regs_table = {
                "name": "general",
                "descr": "General Registers.",
                "regs": [],
            }
            cls.regs.append(general_regs_table)

        # Add 'VERSION' register if this is the first time we are setting up this core
        # (The register will already be present on subsequent setups)
        if len(cls._setup_purpose) < 2:
            # Auto add 'VERSION' register in 'general' registers table if it doesn't exist
            # If it does exist, give an error
            for reg in general_regs_table["regs"]:
                if reg["name"] == "VERSION":
                    raise Exception(
                        cls.name + ": Register 'VERSION' is reserved. Please remove it."
                    )
            else:
                general_regs_table["regs"].append(
                    {
                        "name": "VERSION",
                        "type": "R",
                        "n_bits": 16,
                        "rst_val": build_srcs.version_str_to_digits(cls.version),
                        "addr": -1,
                        "log2n_items": 0,
                        "autologic": True,
                        "descr": "Product version.  This 16-bit register uses nibbles to represent decimal numbers using their binary values. The two most significant nibbles represent the integral part of the version, and the two least significant nibbles represent the decimal part. For example V12.34 is represented by 0x1234.",
                    }
                )

        # Create an instance of the mkregs class inside the mkregs module
        # This instance is only used locally, not affecting status of mkregs imported in other functions/modules
        mkregs_obj = mkregs.mkregs()
        mkregs_obj.config = cls.confs
        # Get register table
        reg_table = mkregs_obj.get_reg_table(cls.regs, no_overlap)

        return mkregs_obj, reg_table

    @classmethod
    def _generate_hw(cls, mkregs_obj, reg_table):
        """Generate common hardware files"""
        if cls.regs:
            mkregs_obj.write_hwheader(
                reg_table, cls.build_dir + "/hardware/src", cls.name
            )
            mkregs_obj.write_lparam_header(
                reg_table, cls.build_dir + "/hardware/simulation/src", cls.name
            )
            mkregs_obj.write_hwcode(
                reg_table, cls.build_dir + "/hardware/src", cls.name
            )

        if cls.confs:
            mk_conf.params_vh(cls.confs, cls.name, cls.build_dir + "/hardware/src")

            mk_conf.conf_vh(cls.confs, cls.name, cls.build_dir + "/hardware/src")

        if cls.ios:
            ios.generate_ports(cls.ios, cls.name, cls.build_dir + "/hardware/src")

    @classmethod
    def _generate_sw(cls, mkregs_obj, reg_table):
        """Generate common software files"""
        if "emb" in cls.flows:
            os.makedirs(cls.build_dir + "/software/src", exist_ok=True)
            if cls.regs:
                mkregs_obj.write_swheader(
                    reg_table, cls.build_dir + "/software/src", cls.name
                )
                mkregs_obj.write_swcode(
                    reg_table, cls.build_dir + "/software/src", cls.name
                )
                mkregs_obj.write_swheader(
                    reg_table, cls.build_dir + "/software/src", cls.name
                )
            mk_conf.conf_h(cls.confs, cls.name, cls.build_dir + "/software/src")

    @classmethod
    def _generate_doc(cls, mkregs_obj, reg_table):
        """Generate common documentation files"""
        if cls.is_top_module and "doc" in cls.flows:
            mk_conf.generate_confs_tex(cls.confs, cls.build_dir + "/document/tsrc")
            ios.generate_ios_tex(cls.ios, cls.build_dir + "/document/tsrc")
            if cls.regs:
                mkregs_obj.generate_regs_tex(
                    cls.regs, reg_table, cls.build_dir + "/document/tsrc"
                )
            blocks.generate_blocks_tex(
                cls.block_groups, cls.build_dir + "/document/tsrc"
            )

    @classmethod
    def _remove_duplicate_sources(cls):
        """Remove sources in the build directory from subfolders that exist in `hardware/src`"""
        # Go through all subfolders defined in PURPOSE_DIRS
        for subfolder in cls.PURPOSE_DIRS.values():
            # Skip hardware folder
            if subfolder == "hardware/src":
                continue

            # Get common srcs between `hardware/src` and current subfolder
            common_srcs = cls.find_common_deep(
                os.path.join(cls.build_dir, "hardware/src"),
                os.path.join(cls.build_dir, subfolder),
            )
            # Remove common sources
            for src in common_srcs:
                os.remove(os.path.join(cls.build_dir, subfolder, src))

    @classmethod
    def _replace_snippet_includes(cls):
        verilog_tools.replace_includes(cls.setup_dir, cls.build_dir)

    @classmethod
    def _run_setup_files(cls):
        flows_setup_files = {
            "sim": cls.setup_dir + "/hardware/simulation/sim_setup.py",
            "fpga": cls.setup_dir + "/hardware/fpga/fpga_setup.py",
            "emb": cls.setup_dir + "/software/sw_setup.py",
            "doc": cls.setup_dir + "/document/doc_setup.py",
        }
        for flow, filepath in flows_setup_files.items():
            # Skip if flow not in flows list
            if flow not in cls.flows:
                continue

            # Skip if file does not exist
            if not os.path.isfile(filepath):
                continue

            module_name = os.path.basename(filepath).split(".")[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            # Define setup_module object, corresponding to this class
            vars(module)["setup_module"] = cls
            # Execute setup file
            spec.loader.exec_module(module)

    @classmethod
    def _setup_submodules(cls, submodule_list):
        """
        Generate or run setup functions for the interfaces/submodules in the given submodules list.
        """
        for submodule in submodule_list:
            _submodule = submodule
            setup_options = {}

            # Split submodule from its setup options (if it is a tuple)
            if type(submodule) == tuple:
                _submodule = submodule[0]
                setup_options = submodule[1]

            # Add 'hardware' purpose by default
            if "purpose" not in setup_options:
                setup_options["purpose"] = "hardware"

            # Don't setup submodules that have a purpose different than
            # "hardware" when this class is not the top module
            if not cls.is_top_module and setup_options["purpose"] != "hardware":
                continue

            # If the submodule purpose is hardware, change that purpose to match the purpose of the current class.
            # (If we setup the current class for simulation, then we want the submodules for simulation aswell)
            if setup_options["purpose"] == "hardware":
                setup_options["purpose"] = cls.get_setup_purpose()

            # Check if should generate with if_gen or setup a submodule.
            if type(_submodule) == dict:
                # Dictionary: generate interface with if_gen
                cls.__generate(_submodule, **setup_options)
            elif issubclass(_submodule, iob_module):
                # Subclass of iob_module: setup the module
                _submodule.__setup(**setup_options)
            else:
                # Unknown type
                raise Exception(
                    f"{iob_colors.FAIL}Unknown type in submodule_list of {cls.name}: {_submodule}{iob_colors.ENDC}"
                )

    @classmethod
    def __generate(cls, vs_name, purpose="hardware"):
        """
        Generate a Verilog snippet with `if_gen.py`.
        """
        dest_dir = os.path.join(cls.build_dir, cls.get_purpose_dir(purpose))

        # set prefixes if they do not exist
        if not "file_prefix" in vs_name:
            vs_name["file_prefix"] = ""
        if not "port_prefix" in vs_name:
            vs_name["port_prefix"] = ""
        if not "wire_prefix" in vs_name:
            vs_name["wire_prefix"] = ""
        
 

    @classmethod
    def get_setup_purpose(cls):
        """Get the purpose of the latest setup.
        :returns str setup_purpose: The latest setup purpose
        """
        if len(cls._setup_purpose) < 1:
            raise Exception(
                f"{iob_colors.FAIL}Module has not been setup!{iob_colors.ENDC}"
            )
        # Return the latest purpose
        return cls._setup_purpose[-1]

    @classmethod
    def get_purpose_dir(cls, purpose):
        """Get output directory based on the purpose given."""
        assert (
            purpose in cls.PURPOSE_DIRS
        ), f"{iob_colors.FAIL}Unknown purpose {purpose}{iob_colors.ENDC}"
        return cls.PURPOSE_DIRS[purpose]

    @classmethod
    def __create_build_dir(cls):
        """Create build directory. Must be called from the top module."""
        assert (
            cls.is_top_module
        ), f"{iob_colors.FAIL}Module {cls.name} is not a top module!{iob_colors.ENDC}"
        os.makedirs(cls.build_dir, exist_ok=True)
        config_build_mk(cls)
        # Create hardware directories
        os.makedirs(f"{cls.build_dir}/hardware/src", exist_ok=True)
        if "sim" in cls.flows:
            os.makedirs(f"{cls.build_dir}/hardware/simulation/src", exist_ok=True)
        if "fpga" in cls.flows:
            os.makedirs(f"{cls.build_dir}/hardware/fpga/src", exist_ok=True)

        shutil.copyfile(
            f"{build_srcs.LIB_DIR}/build.mk", f"{cls.build_dir}/Makefile"
        )  # Copy generic MAKEFILE

    @classmethod
    def _copy_srcs(cls, exclude_file_list=[], highest_superclass=None):
        """Copy module sources to the build directory from every subclass in between `iob_module` and `cls`, inclusive.
        The function will not copy sources from classes that have no setup_dir (empty string)
        cls: Lowest subclass
        (implicit: iob_module: highest subclass)
        :param list exclude_file_list: list of strings, each string representing an ignore pattern for the source files.
                                       For example, using the ignore pattern '*.v' would prevent from copying every Verilog source file.
                                       Note, if want to ignore a file that is going to be renamed with the new core name,
                                       we would still use the old core name in the ignore patterns.
                                       For example, if we dont want it to generate the 'new_name_firmware.c' based on the 'old_name_firmware.c',
                                       then we should add 'old_name_firmware.c' to the ignore list.
        :param class highest_superclass: If specified, only copy sources from this subclass and up to specified class. By default, highest_superclass=iob_module.
        """
        previously_setup_dirs = []
        # Select between specified highest_superclass or this one (iob_module)
        highest_superclass = highest_superclass or __class__

        # List of classes, starting from highest superclass (iob_module), down to lowest subclass (cls)
        classes = cls.__mro__[cls.__mro__.index(highest_superclass) :: -1]

        # Go through every subclass, starting for highest superclass to the lowest subclass
        for module_class in classes:
            # Skip classes without setup_dir
            if not module_class.setup_dir:
                continue

            # Skip class if we already setup its directory (it may have inherited the same dir from the superclass)
            if module_class.setup_dir in previously_setup_dirs:
                continue

            previously_setup_dirs.append(module_class.setup_dir)

            # Files that should always be copied
            dir_list = [
                "hardware/src",
                "software",
            ]
            # Files that should only be copied if it is top module
            if cls.is_top_module:
                dir_list += [
                    "hardware/simulation",
                    "hardware/fpga",
                    "hardware/syn",
                    "hardware/lint",
                ]

            # Copy sources
            for directory in dir_list:
                # Skip this directory if it does not exist
                if not os.path.isdir(os.path.join(module_class.setup_dir, directory)):
                    continue

                # If we are handling the `hardware/src` directory,
                # copy to the correct destination based on `_setup_purpose`.
                if directory == "hardware/src":
                    dst_directory = cls.get_purpose_dir(cls.get_setup_purpose())
                else:
                    dst_directory = directory

                # Copy tree of this directory, renaming files, and overriding destination ones.
                shutil.copytree(
                    os.path.join(module_class.setup_dir, directory),
                    os.path.join(cls.build_dir, dst_directory),
                    dirs_exist_ok=True,
                    copy_function=cls.copy_with_rename(module_class.name, cls.name),
                    ignore=shutil.ignore_patterns(*exclude_file_list),
                )

            # Copy document directory if cls is the top module and it has documentation
            if cls.is_top_module and "doc" in cls.flows:
                shutil.copytree(
                    os.path.join(module_class.setup_dir, "document"),
                    os.path.join(cls.build_dir, "document"),
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*exclude_file_list),
                )

    ###############################################################
    # Utility methods
    ###############################################################

    @staticmethod
    def update_dict_list(dict_list, new_items):
        """Update a list of dictionaries with new items given in a list

        :param list dict_list: List of dictionaries, where each item is a dictionary that has a "name" key
        :param list new_items: List of dictionaries, where each item is a dictionary that has a "name" key and should be inserted into the dict_list
        """
        for item in new_items:
            for _item in dict_list:
                if _item["name"] == item["name"]:
                    _item.update(item)
                    break
            else:
                dict_list.append(item)

    @staticmethod
    def find_common_deep(path1, path2):
        """Find common files (recursively) inside two given directories
        Taken from: https://stackoverflow.com/a/51625515
        :param str path1: Directory path 1
        :param str path2: Directory path 2
        """
        return set.intersection(
            *(
                set(
                    os.path.relpath(os.path.join(root, file), path)
                    for root, _, files in os.walk(path)
                    for file in files
                )
                for path in (path1, path2)
            )
        )

    @staticmethod
    def copy_with_rename(old_core_name, new_core_name):
        """Creates a function that:
        - Renames any '<old_core_name>' string inside the src file and in its filename, to the given '<new_core_name>' string argument.
        """

        def copy_func(src, dst):
            dst = os.path.join(
                os.path.dirname(dst),
                os.path.basename(
                    dst.replace(old_core_name, new_core_name).replace(
                        old_core_name.upper(), new_core_name.upper()
                    )
                ),
            )
            # print(f"### DEBUG: {src} {dst}")
            try:
                file_perms = os.stat(src).st_mode
                with open(src, "r") as file:
                    lines = file.readlines()
                for idx in range(len(lines)):
                    lines[idx] = (
                        lines[idx]
                        .replace(old_core_name, new_core_name)
                        .replace(old_core_name.upper(), new_core_name.upper())
                    )
                with open(dst, "w") as file:
                    file.writelines(lines)
            except:
                shutil.copyfile(src, dst)
            # Set file permissions equal to source file
            os.chmod(dst, file_perms)

        return copy_func
