ifeq ($(filter iob_counter, $(HW_MODULES)),)

# Add to modules list
HW_MODULES+=iob_counter

# Sources
SRC+=$(BUILD_VSRC_DIR)/iob_counter.v

# Copy the sources to the build directory 
%/iob_counter.v: $(LIB_DIR)/hardware/counter/iob_counter/iob_counter.v
	cp $< $@

endif
