# Inkluder felles regler fra Makefile-felles.mk
include Makefile-felles.mk

# Briar-spesifikke variabler
BRIAR_URL=https://briarproject.org/apk/briar.apk
BRIAR_APK_PATH=./briar.apk
BRIAR_APP_NAME=org.briarproject.briar.android

# Last ned APK-filen hvis den ikke allerede er lastet ned
download-briar:
	@if [ ! -f $(BRIAR_APK_PATH) ]; then \
		echo "Downloading APK from $(BRIAR_URL)..."; \
		curl -o $(BRIAR_APK_PATH) $(BRIAR_URL); \
	else \
		echo "APK already downloaded at $(BRIAR_APK_PATH)"; \
	fi

# Installer APK på én enhet
install-one: download-briar
	@echo "Enter the device name (e.g., Charlie): "; \
	read DEVICE_NAME; \
	$(MAKE) -f Makefile-felles.mk install-on-device DEVICE_NAME=$$DEVICE_NAME APK_PATH=$(BRIAR_APK_PATH)

# Installer APK på alle enheter
install-all: download-briar
	@echo "Installing APK on all devices listed in enheter.conf..."; \
	for DEVICE_NAME in $$(zsh -c 'source $(FELLES_SCRIPT) && echo $${(k)device_info_map}'); do \
		$(MAKE) -f Makefile-felles.mk install-on-device DEVICE_NAME=$$DEVICE_NAME APK_PATH=$(BRIAR_APK_PATH); \
	done

uninstall-one:
	@echo "Enter the device name (e.g., Charlie): "; \
	read DEVICE_NAME; \
	echo "Uninstalling $(BRIAR_APP_NAME) on device $$DEVICE_NAME..."; \
	$(MAKE) -f Makefile-felles.mk uninstall-on-device DEVICE_NAME=$$DEVICE_NAME APP_NAME=$(BRIAR_APP_NAME)
