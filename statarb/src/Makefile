include $(SRC_DIR)/Makefile.inc

DIRFLAGS = -p -v -m 750
RSYNCFLAGS = -avuzb --exclude "*~" --exclude ".*" --exclude "\#*" --exclude "*.pyc" --exclude "*.o"

all:
	make -C java all
	make -C python all
cpp:
	make -C cpp all
java:
	make -C java all
web:
	make -C web/java all install	
build:
	mkdir $(DIRFLAGS) $(ROOT_DIR)/config
	mkdir $(DIRFLAGS) $(ROOT_DIR)/config/sources
	mkdir $(DIRFLAGS) $(ROOT_DIR)/bin
	mkdir $(DIRFLAGS) $(ROOT_DIR)/cron
	mkdir $(DIRFLAGS) $(ROOT_DIR)/R
	mkdir $(DIRFLAGS) $(ROOT_DIR)/research
	mkdir $(DIRFLAGS) $(ROOT_DIR)/obj
	mkdir $(DIRFLAGS) $(ROOT_DIR)/obj/python
	mkdir $(DIRFLAGS) $(ROOT_DIR)/obj/jav
ifneq ($(ROOT_DIR),/apps/ase)
	ln -s /apps/ase/install $(ROOT_DIR)
endif

install:
	rsync $(RSYNCFLAGS) $(SRC_DIR)/bin/* $(BIN_DIR)
	rsync $(RSYNCFLAGS) $(SRC_DIR)/perl/* $(BIN_DIR)
	rsync $(RSYNCFLAGS) $(SRC_DIR)/config/* $(CONFIG_DIR)
	rsync $(RSYNCFLAGS) $(SRC_DIR)/R/*.R $(R_DIR)	
	rsync $(RSYNCFLAGS) $(SRC_DIR)/python/bin/*.py $(BIN_DIR)
	rsync $(RSYNCFLAGS) $(SRC_DIR)/python/lib $(OBJ_DIR)/python
	rsync $(RSYNCFLAGS) $(SRC_DIR)/cron/*.cron $(ROOT_DIR)/cron
	rsync $(RSYNCFLAGS) $(SRC_DIR)/exec/rbin/* $(BIN_DIR)
	rsync $(RSYNCFLAGS) $(SRC_DIR)/exec/python/rbin/* $(BIN_DIR)
	make -C java install
#do it at end so that asemail.sh exists
ifeq ($(ROOT_DIR),/apps/ase)
	echo Installing to $(ROOT_DIR) | $(BIN_DIR)/asemail.sh INSTALLING on $(HOSTNAME)...
endif

clean:
	$(RM) $(OBJ_DIR)/java/*
	$(RM) $(OBJ_DIR)/python/*
	$(RM) $(ROOT_DIR)/cron/*
	$(RM) $(ROOT_DIR)/config/*

clean_src:
	$(RM) `find $(SRC_DIR) -name "*~"` 
	$(RM) `find $(SRC_DIR) -name ".#*"` 
	$(RM) `find $(SRC_DIR) -name "#*#"` 
	$(RM) `find $(SRC_DIR) -name "*.pyc"` 
