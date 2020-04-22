##
## Bulid and load Metatab data packages
## for comments and course-enrollments
##


REPO_ROOT=$(shell git rev-parse --show-toplevel)

PACK_DIR=$(REPO_ROOT)/_build

GROUP_ARG=$(and $(GROUPS),"-g $(GROUPS)" )
TAG_ARG=$(and $(TAGS),"-t $(TAGS)" )

# Optional profile name in .aws/credentials
S3_PROFILE_ARG=$(and $(S3_PROFILE),"-p$(S3_PROFILE)" )

.PHONY: $(PACK_DIR) clean build s3 ckan list info wp touch

default: build ;

# List all of the targets
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xargs



PACKAGE_MARKERS = $(patsubst %,$(PACK_DIR)/%.build,$(PACKAGE_NAMES))
S3_MARKERS = $(patsubst %,$(PACK_DIR)/%.s3,$(PACKAGE_NAMES))
CKAN_MARKERS = $(patsubst %,$(PACK_DIR)/%.ckan,$(PACKAGE_NAMES))
WP_MARKERS = $(patsubst %,$(PACK_DIR)/%.wp,$(PACKAGE_NAMES))

# These are never actually created
TOUCH_MARKERS = $(patsubst %,$(PACK_DIR)/%.touch,$(PACKAGE_NAMES))
HASH_MARKERS = $(patsubst %,$(PACK_DIR)/%.hash,$(PACKAGE_NAMES))


$(PACK_DIR):
	mkdir -p $(PACK_DIR)


# touch the metadata, so the package is rebuilt
$(PACK_DIR)/%.touch :
	@echo TOUCH $*
	@mkdir -p $(PACK_DIR)
	@cd  $* && touch metadata.csv

# Update the hashes for the packages.
$(PACK_DIR)/%.hash :
	@echo HASH $*
	@mkdir -p $(PACK_DIR)
	@cd  $* && mp touch -W

# Build a package file in the packages
# directory
$(PACK_DIR)/%.build :  %/metadata.csv
	@echo BUILD $* from $*
	@mkdir -p $(PACK_DIR)
	cd  $* && mp -q --exceptions build -X -fzr && \
	 cd .. && touch $(PACK_DIR)/$*.build
	mp -q index $*
	@# If the file has not changed, update the s3 marker so the unchanged package
	@# isn't uploaded. If it has, update the hashes.
	@( mp touch -C $*  && touch $(PACK_DIR)/%.s3 ) || (  mp touch -W $*)

$(PACK_DIR)/%.build :  %/metadata.txt
	@echo BUILD $* from $*
	@mkdir -p $(PACK_DIR)
	@cd  $* && mp -q --exceptions build -X -fzr && \
	 cd .. && touch $(PACK_DIR)/$*.build
	@mp -q index $*

$(PACK_DIR)/%.s3: $(PACK_DIR)/%.build
ifndef S3_BUCKET
	$(error S3_BUCKET is undefined)
endif
	@echo S3 $* \( $@ \)
	@mp -q s3 -r -s $(S3_BUCKET) $(S3_PROFILE_ARG) $*  && touch $(PACK_DIR)/$*.s3
	@touch -r $(PACK_DIR)/$*.build $*/metadata.csv # mp s3 updates the metadata, but we don't want to re-trigger build

$(PACK_DIR)/%.ckan: $(PACK_DIR)/%.s3
	@echo CKAN $* \( $@ \)
	@mp ckan $(GROUP_ARG) $(TAG_ARG) $* && touch $(PACK_DIR)/$*.ckan
	@touch -r $(PACK_DIR)/$*.build $*/metadata.csv # mp ckan updates the metadata, but we don't want to re-trigger build

$(PACK_DIR)/%.wp: $(PACK_DIR)/%.s3
ifndef WP_SITE
	$(error WP_SITE is undefined)
endif
	@echo WP $* \( $@ \)
	@mp -q wp -r $(GROUP_ARG) $(TAG_ARG) -s $(WP_SITE)  -p $* && touch $(PACK_DIR)/$*.wp
	@touch -r $(PACK_DIR)/$*.build $*/metadata.csv # mp ckan updates the metadata, but we don't want to re-trigger build

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

touch: $(TOUCH_MARKERS) ;

hash: $(HASH_MARKERS) ;

clean-s3:
	rm -f (PACK_DIR)/*.s3

ckan: $(CKAN_MARKERS) ;


clean-ckan:
	rm -f $(PACK_DIR)/*.ckan
