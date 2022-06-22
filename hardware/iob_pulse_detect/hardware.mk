
ifneq (iob_pulse_detect,$(filter iob_pulse_detect, $(HW_MODULES)),)

# Add to modules list
HW_MODULES+=iob_pulse_detect

# Sources
VSRC+=$(BUILD_VSRC_DIR)/iob_pulse_detect.v

# Copy the sources to the build directory 
$(BUILD_VSRC_DIR)/iob_pulse_detect.v:hardware/iob_pulse_detect/iob_pulse_detect.v
	cp $< $(BUILD_VSRC_DIR)

endif
