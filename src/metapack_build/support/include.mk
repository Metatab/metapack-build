##
## Bulid and load Metatab data packages
## for comments and course-enrollments
##




REPO_ROOT=$(shell git rev-parse --show-toplevel)

PACK_DIR=$(REPO_ROOT)/_build

GROUP_ARG=$(and $(GROUPS),"-g $(GROUPS)" )
TAG_ARG=$(and $(TAGS),"-t $(TAGS)" )

.PHONY: $(PACK_DIR) clean build s3 ckan list info wp

default: build ;

# List all of the targets
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xargs


PACKAGE_MARKERS = $(patsubst %,$(PACK_DIR)/%.build,$(PACKAGE_NAMES))
S3_MARKERS = $(patsubst %,$(PACK_DIR)/%.s3,$(PACKAGE_NAMES))
CKAN_MARKERS = $(patsubst %,$(PACK_DIR)/%.ckan,$(PACKAGE_NAMES))
WP_MARKERS = $(patsubst %,$(PACK_DIR)/%.wp,$(PACKAGE_NAMES))

$(PACK_DIR):
	mkdir -p $(PACK_DIR)


# Build a package file in the packages
# directory
$(PACK_DIR)/%.build :  %/metadata.csv
	@echo ======== BUILD $* from $* =======
	mkdir -p $(PACK_DIR)
	cd  $* && mp --exceptions build -f -z && \
	cd .. && touch $(PACK_DIR)/$*.build
	mp index $*

$(PACK_DIR)/%.build :  %/metadata.txt
	@echo ======== BUILD $* from $* =======
	mkdir -p $(PACK_DIR)
	cd  $* && mp --exceptions build -f -z && \
	cd .. && touch $(PACK_DIR)/$*.build
	mp index $*

$(PACK_DIR)/%.s3: $(PACK_DIR)/%.build
ifndef S3_BUCKET
	$(error S3_BUCKET is undefined)
endif
	@echo ======== S3 $* \( $@ \) =======
	mp s3 -s $(S3_BUCKET) $*  && touch $(PACK_DIR)/$*.s3
	touch -r $(PACK_DIR)/$*.build $*/metadata.csv # mp s3 updates the metadata, but we don't want to re-trigger build

$(PACK_DIR)/%.ckan: $(PACK_DIR)/%.s3
	@echo ======== CKAN $* \( $@ \) =======
	mp ckan $(GROUP_ARG) $(TAG_ARG) $* && touch $(PACK_DIR)/$*.ckan
	touch -r $(PACK_DIR)/$*.build $*/metadata.csv # mp ckan updates the metadata, but we don't want to re-trigger build

$(PACK_DIR)/%.wp: $(PACK_DIR)/%.s3
ifndef WP_SITE
	$(error WP_SITE is undefined)
endif
	@echo ======== CKAN $* \( $@ \) =======
	mp wp $(GROUP_ARG) $(TAG_ARG) -s $(WP_SITE)  -p $* && touch $(PACK_DIR)/$*.wp
	touch -r $(PACK_DIR)/$*.build $*/metadata.csv # mp ckan updates the metadata, but we don't want to re-trigger build

# Make a package, using the packages'
# non-versioned names
$(PACKAGE_NAMES): %:$(PACK_DIR)/%.build ;

# Make all packages


info:
	@echo ======
	@echo PACKAGE_MARKERS=$(PACKAGE_MARKERS)
	@echo PACKAGE_NAMES=$(PACKAGE_NAMES)

clean:
	rm -rf $(PACK_DIR)
	mkdir -p $(PACK_DIR)
	find . -name _packages -exec rm -rf {} \;

clean-cache:
	rm -rf "$(shell mp info -C)"/library.metatab.org

build: $(PACKAGE_MARKERS) ;



s3: $(S3_MARKERS) ;

wp: $(WP_MARKERS) ;

clean-s3:
	rm -f (PACK_DIR)/*.s3

ckan: $(CKAN_MARKERS) ;


clean-ckan:
	rm -f $(PACK_DIR)/*.ckan
