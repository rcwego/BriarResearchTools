# Inkluder felles regler fra Makefile-felles.mk
include Makefile-felles.mk

# Frida-spesifikke variabler
FRIDA_LOCAL_FILE_ARM=./frida-server-16.5.6-android-arm64
FRIDA_LOCAL_FILE_x8664=./frida-server-16.5.6-android-x86_64
FRIDA_REMOTE_PATH=/data/local/tmp/frida-server

# Hent enhets-ID fra felles script (justert for device_info_map)
get-device-id = $(shell zsh -c 'source $(FELLES_SCRIPT) && echo $$($(FELLES_SCRIPT) && hent_enhets_id $(DEVICE_NAME))')

# Funksjon for å installere Frida-server
install-frida-on-device:
	@DEVICE_ID=$$(zsh -c 'source $(FELLES_SCRIPT) && echo $$($(FELLES_SCRIPT) && hent_enhets_id $(DEVICE_NAME))'); \
	if [ -z "$$DEVICE_ID" ]; then \
		echo "Ingen enhet med navnet $(DEVICE_NAME) funnet!"; \
		exit 1; \
	fi; \
	DEVICE_TYPE=$$(zsh -c 'source $(FELLES_SCRIPT) && echo $$($(FELLES_SCRIPT) && get_device_arkitektur $(DEVICE_NAME))'); \
	echo "Fant enhet $$DEVICE_ID med navn $(DEVICE_NAME) og type $$DEVICE_TYPE"; \
	if [ "$$DEVICE_TYPE" = "x8664" ]; then \
		FRIDA_LOCAL_FILE=$(FRIDA_LOCAL_FILE_x8664); \
		echo "Installerer Frida-server for x86_64-arkitektur..."; \
	elif [ "$$DEVICE_TYPE" = "arm64" ]; then \
		FRIDA_LOCAL_FILE=$(FRIDA_LOCAL_FILE_ARM); \
		echo "Installerer Frida-server for ARM64-arkitektur..."; \
	else \
		echo "Ukjent enhetstype $$DEVICE_TYPE!"; \
		exit 1; \
    fi; \
	echo "Installerer på enhet $$DEVICE_ID med navn $(DEVICE_NAME)..."; \
	adb -s $$DEVICE_ID push $$FRIDA_LOCAL_FILE $(FRIDA_REMOTE_PATH); \
	adb -s $$DEVICE_ID shell 'chmod 755 $(FRIDA_REMOTE_PATH)'; \
	adb -s $$DEVICE_ID shell 'ls -lha $(FRIDA_REMOTE_PATH)'

# Installer Frida-server på én enhet
install-one:
	@echo "Skriv inn enhetsnavnet (f.eks. Charlie): "; \
	read DEVICE_NAME; \
	$(MAKE) -f Makefile-frida.mk install-frida-on-device DEVICE_NAME=$$DEVICE_NAME

# Installer Frida-server på alle enheter
install-all:
	@echo "Installerer Frida-server på alle enheter listet i enheter.conf..."; \
	for DEVICE_NAME in $$(zsh -c 'source $(FELLES_SCRIPT) && echo $${(k)device_info_map}'); do \
		$(MAKE) -f Makefile-frida.mk install-frida-on-device DEVICE_NAME=$$DEVICE_NAME; \
	done
