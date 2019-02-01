include $(SRC_DIR)/Makefile.inc

JFLAGS = -g
JFLAGS += -classpath $(CLASSPATH)
#JAVAC = /apps/logs/ase/install/local/jdk/bin/javac

.SUFFIXES: .java .class
.java.class:
	$(JAVAC) $(JFLAGS) $*.java

CLASSES = \

all:
	$(JAVAC) $(JFLAGS) -d $(OBJ_DIR)/java `find . -name "*.java"`

install:
	$(JAR) cvf $(OBJ_DIR)/java/ase.jar $(OBJ_DIR)/java/ase
