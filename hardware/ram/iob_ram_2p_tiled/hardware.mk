ifeq ($(filter iob_ram_2p_tiled, $(HW_MODULES)),)

# Add to modules list
HW_MODULES+=iob_ram_2p_tiled

# Submodules
include hardware/ram/iob_ram_2p/hardware.mk

# Sources
VSRC+=$(BUILD_VSRC_DIR)/iob_ram_2p_tiled.v

# Copy the sources to the build directory
$(BUILD_VSRC_DIR)/iob_ram_2p_tiled.v:hardware/ram/iob_ram_2p_tiled/iob_ram_2p_tiled.v
	cp $< $(BUILD_VSRC_DIR)

endif
