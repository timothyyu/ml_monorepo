include $(SRC_DIR)/Makefile.inc

all:
	cd $(INSTALL_DIR)/infra/dev; bjam $(SRC_DIR)/cpp//superbars link=static release toolset=gcc-4.1
install:
	cp $(CPFLAGS) `find $(OBJ_DIR)/cpp/build/bars/gcc-4.1/release/link-static/threading-multi -name superbars` $(BIN_DIR)
clean:
	$(RM) $(OBJ_DIR)/cpp/build
debug:
	cd $(INSTALL_DIR)/infra/dev; bjam $(SRC_DIR)/cpp//superbars link=static debug toolset=gcc-4.1
