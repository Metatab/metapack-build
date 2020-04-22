##
## Bulid and load Metatab data packages
## for comments and course-enrollments
##


REPO_ROOT=$(shell git rev-parse --show-toplevel)

GROUP_ARG=$(and $(GROUPS),"-g $(GROUPS)" )
TAG_ARG=$(and $(TAGS),"-t $(TAGS)" )

# Optional profile name in .aws/credentials
S3_PROFILE_ARG=$(and $(S3_PROFILE),"-p$(S3_PROFILE)" )

.PHONY:  clean build s3 ckan list info wp touch

default: build ;

# List all of the targets
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xarg

# Build a package file in the packages
# directory
%.build :  %/metadata.csv
	@echo ==== $* ====
	@ cd $*  && \
	 	mp -q  make -r  -b -s $(S3_BUCKET) -w $(WP_SITE) $(GROUP_ARG) $(TAG_ARG) || \
	 	echo "\033[0;31mFAILED: $*\033[0m"

# Make a package, using the packages'
# non-versioned names
$(PACKAGE_NAMES): %: %.build ;

info:
	@echo ======
	@echo PACKAGE_NAMES=$(PACKAGE_NAMES)

clean:
	find . -name _packages -exec rm -rf {} \;

clean-cache:
	rm -rf "$(shell mp info -C)"/library.metatab.org

build: $(PACKAGE_NAMES) ;
