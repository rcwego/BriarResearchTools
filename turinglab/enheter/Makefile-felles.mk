# Sjekk hvor felles script befinner seg
FELLES_SCRIPT=./felles.sh

# Felles ADB-administrasjon
start-adb:
	@echo "Starting ADB server..."
	adb start-server

stop-adb:
	@echo "Stopping ADB server..."
	adb kill-server

devices:
	@echo "Listing connected devices..."
	adb devices

# Felles funksjon for å installere APK på en enhet
install-on-device:
	@echo "Using FELLES_SCRIPT at: $(FELLES_SCRIPT)"; \
	if [ ! -f $(FELLES_SCRIPT) ]; then \
		echo "Felles script not found at $(FELLES_SCRIPT)"; \
		exit 1; \
	fi; \
	DEVICE_ID=$$(zsh -c 'source $(FELLES_SCRIPT) && echo $$(hent_enhets_id $(DEVICE_NAME))'); \
	if [ -z "$$DEVICE_ID" ]; then \
		echo "Device $(DEVICE_NAME) not found!"; \
		exit 1; \
	fi; \
	echo "Installing APK on device $$DEVICE_ID..."; \
	adb -s $$DEVICE_ID install -r $(APK_PATH)

uninstall-on-device:
	@echo "Using FELLES_SCRIPT at: $(FELLES_SCRIPT)"; \
	if [ ! -f $(FELLES_SCRIPT) ]; then \
		echo "Felles script not found at $(FELLES_SCRIPT)"; \
		exit 1; \
	fi; \
	DEVICE_ID=$$(zsh -c 'source $(FELLES_SCRIPT) && echo $$(hent_enhets_id $(DEVICE_NAME))'); \
	if [ -z "$$DEVICE_ID" ]; then \
		echo "Device $(DEVICE_NAME) not found!"; \
		exit 1; \
	fi; \
	echo "Uninstalling $(APP_NAME) on device $$DEVICE_ID..."; \
	adb -s $$DEVICE_ID uninstall $(APP_NAME)

