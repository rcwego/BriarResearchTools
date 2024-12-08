# Sett stien til felles script
FELLES_SCRIPT=./ressurser/felles.sh

# Inkluder felles regler fra Makefile-felles.mk
include Makefile-felles.mk

# Magisk-spesifikke variabler
MAGISK_URL=https://github.com/topjohnwu/Magisk/releases/download/v27.0/Magisk-v27.0.apk
MAGISK_APK_PATH=./Magisk-v27.0.apk

# Last ned APK-filen hvis den ikke allerede er lastet ned
download-magisk:
	@if [ ! -f $(MAGISK_APK_PATH) ]; then \
		echo "Downloading Magisk APK from $(MAGISK_URL)..."; \
		curl -o $(MAGISK_APK_PATH) $(MAGISK_URL); \
	else \
		echo "Magisk APK already downloaded at $(MAGISK_APK_PATH)"; \
	fi

# Installer APK på én enhet fra lokal fil
install-one: download-magisk
	@echo "Enter the device name (e.g., Charlie): "; \
	read DEVICE_NAME; \
	$(MAKE) -f Makefile-felles.mk install-on-device DEVICE_NAME=$$DEVICE_NAME APK_PATH=$(MAGISK_APK_PATH)

# Installer APK på alle enheter fra lokal fil
install-all: download-magisk
	@echo "Installing Magisk APK on all devices listed in enheter.conf..."; \
	source $(FELLES_SCRIPT); \
	for DEVICE_NAME in $$(source $(FELLES_SCRIPT) && echo $${(k)device_map}); do \
		$(MAKE) -f Makefile-felles.mk install-on-device DEVICE_NAME=$$DEVICE_NAME APK_PATH=$(MAGISK_APK_PATH); \
	done
