VERSION := 0.1.0

LANGUAGE_NAME := tree-sitter-sqlite3

# repository
SRC_DIR := src

TS ?= tree-sitter

# install directory layout
PREFIX ?= /usr/local
INCLUDEDIR ?= $(PREFIX)/include
LIBDIR ?= $(PREFIX)/lib
PCLIBDIR ?= $(LIBDIR)/pkgconfig

# source files
PARSER_REPO_URL := $(shell sed -n 's/.*"url": "\(.*\)".*/\1/p' tree-sitter.json | head -n1)

PARSER_URL := $(shell echo $(PARSER_REPO_URL) | sed 's/git+//' | sed 's/\.git$$//')

SRC_DIR_FULL := bindings/c

# ABI versioning
SONAME_MAJOR := 0
SONAME_MINOR := 0

# OS
ifeq ($(shell uname),Darwin)
	SOEXT = dylib
	SOEXTVER_MAJOR = $(SONAME_MAJOR).$(SOEXT)
	SOEXTVER = $(SONAME_MAJOR).$(SONAME_MINOR).$(SOEXT)
	LINKSHARED := $(LINKSHARED)-dynamiclib -Wl,
	ifneq ($(ADDITIONAL_LIBS),)
		LINKSHARED := $(LINKSHARED)$(ADDITIONAL_LIBS),
	endif
	LINKSHARED := $(LINKSHARED)-install_name,$(LIBDIR)/lib$(LANGUAGE_NAME).$(SOEXTVER),-rpath,@executable_path/../Frameworks
else
	SOEXT = so
	SOEXTVER_MAJOR = $(SOEXT).$(SONAME_MAJOR)
	SOEXTVER = $(SOEXT).$(SONAME_MAJOR).$(SONAME_MINOR)
	LINKSHARED := $(LINKSHARED)-shared -Wl,
	ifneq ($(ADDITIONAL_LIBS),)
		LINKSHARED := $(LINKSHARED)$(ADDITIONAL_LIBS)
	endif
	LINKSHARED := $(LINKSHARED)-soname,lib$(LANGUAGE_NAME).$(SOEXTVER_MAJOR)
endif
ifneq ($(filter $(shell uname),FreeBSD NetBSD DragonFly),)
	PCLIBDIR := $(PREFIX)/libdata/pkgconfig
endif

# flags
override CFLAGS += -O3 -Wall -Wextra -I$(SRC_DIR)

# objects
OBJS := $(addsuffix .o,$(basename $(wildcard $(SRC_DIR)/*.c)))

# targets
all: lib$(LANGUAGE_NAME).a lib$(LANGUAGE_NAME).$(SOEXT) $(LANGUAGE_NAME).pc

lib$(LANGUAGE_NAME).a: $(OBJS)
	$(AR) rcs $@ $^

lib$(LANGUAGE_NAME).$(SOEXT): $(OBJS)
	$(CC) $(LDFLAGS) $(LINKSHARED) $^ $(LDLIBS) -o $@
ifneq ($(STRIP),)
	$(STRIP) $@
endif

$(LANGUAGE_NAME).pc: bindings/c/$(LANGUAGE_NAME).pc.in
	sed -e 's|@URL@|$(PARSER_URL)|' \
		-e 's|@VERSION@|$(VERSION)|' \
		-e 's|@LIBDIR@|$(LIBDIR)|' \
		-e 's|@INCLUDEDIR@|$(INCLUDEDIR)|' \
		-e 's|@REQUIRES@|$(REQUIRES)|' \
		-e 's|@ADDITIONAL_LIBS@|$(ADDITIONAL_LIBS)|' \
		-e 's|=$(PREFIX)|=$${prefix}|' \
		-e 's|@PREFIX@|$(PREFIX)|' $< > $@

$(SRC_DIR)/parser.c: grammar.js
	$(TS) generate $<

install: all
	install -d '$(DESTDIR)$(LIBDIR)' '$(DESTDIR)$(INCLUDEDIR)'/tree_sitter '$(DESTDIR)$(PCLIBDIR)'
	install -m644 bindings/c/$(LANGUAGE_NAME).h '$(DESTDIR)$(INCLUDEDIR)'/tree_sitter/$(LANGUAGE_NAME).h
	install -m644 $(LANGUAGE_NAME).pc '$(DESTDIR)$(PCLIBDIR)'/$(LANGUAGE_NAME).pc
	install -m644 lib$(LANGUAGE_NAME).a '$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).a
	install -m755 lib$(LANGUAGE_NAME).$(SOEXT) '$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).$(SOEXTVER)
	ln -sf lib$(LANGUAGE_NAME).$(SOEXTVER) '$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).$(SOEXTVER_MAJOR)
	ln -sf lib$(LANGUAGE_NAME).$(SOEXTVER_MAJOR) '$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).$(SOEXT)

uninstall:
	$(RM) '$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).a \
		'$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).$(SOEXTVER) \
		'$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).$(SOEXTVER_MAJOR) \
		'$(DESTDIR)$(LIBDIR)'/lib$(LANGUAGE_NAME).$(SOEXT) \
		'$(DESTDIR)$(INCLUDEDIR)'/tree_sitter/$(LANGUAGE_NAME).h \
		'$(DESTDIR)$(PCLIBDIR)'/$(LANGUAGE_NAME).pc

clean:
	$(RM) $(OBJS) $(LANGUAGE_NAME).pc lib$(LANGUAGE_NAME).a lib$(LANGUAGE_NAME).$(SOEXT)

test:
	$(TS) test

.PHONY: all install uninstall clean test
