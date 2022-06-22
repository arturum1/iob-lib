
ifneq (axiinterconnect,$(filter axiinterconnect, $(HW_MODULES)))

# Add to modules list
HW_MODULES+=axiinterconnect


VSRC+=$(BUILD_VSRC_DIR)/axi_interconnect.v $(BUILD_VSRC_DIR)/arbiter.v $(BUILD_VSRC_DIR)/priority_encoder.v


$(BUILD_VSRC_DIR)/axi_interconnect.v: $(V_AXI_DIR)/rtl/axi_interconnect.v
	cp $< $(BUILD_VSRC_DIR)

$(BUILD_VSRC_DIR)/arbiter.v: $(V_AXI_DIR)/rtl/arbiter.v
	cp $< $(BUILD_VSRC_DIR)

$(BUILD_VSRC_DIR)/priority_encoder.v: $(V_AXI_DIR)/rtl/priority_encoder.v
	cp $< $(BUILD_VSRC_DIR)


endif
