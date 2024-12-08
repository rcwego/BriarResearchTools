#!/usr/bin/env zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map
source "$BASE_DIR/../../ressurser/felles.sh"

# Destinasjonsmappen kan tas inn som et argument, standard er ./pakkedumper
LOCAL_PACKETDUMP_DIR=${1:-./pakkedumper}

# Funksjon for å hente pakkedumpfiler fra WiFi- og Bluetooth-katalogene på enhetene
function pull_packetdumps {
  local DEVICE=$2
  local NAME=$1
  
  LOCAL_WIFI_DIR="${LOCAL_PACKETDUMP_DIR}/${NAME}/wifi"
  LOCAL_TOR_DIR="${LOCAL_PACKETDUMP_DIR}/${NAME}/tor"
  LOCAL_BT_DIR="${LOCAL_PACKETDUMP_DIR}/${NAME}/bt"

  # Opprett lokale kataloger hvis de ikke eksisterer
  echo "$LOCAL_WIFI_DIR"
  echo "$LOCAL_TOR_DIR"
  echo "$LOCAL_BT_DIR"
  mkdir -p "$LOCAL_WIFI_DIR"
  mkdir -p "$LOCAL_TOR_DIR"
  mkdir -p "$LOCAL_BT_DIR"
  
  echo "Henter WiFi fra $NAME ($DEVICE)..."
  adb -s $DEVICE shell "ls $WIFI_DIR/*.*" 2>&1 | while read -r file; do
    adb -s $DEVICE pull "$file" "$LOCAL_WIFI_DIR/" 2>&1
  done
  echo "WiFi hentet fra $NAME ($DEVICE)"
  
  echo "Henter Tor fra $NAME ($DEVICE)..."
  adb -s $DEVICE shell "ls $TOR_DIR/*.*" 2>&1 | while read -r file; do
    adb -s $DEVICE pull "$file" "$LOCAL_TOR_DIR/" 2>&1
  done
  echo "Tor hentet fra $NAME ($DEVICE)"

  echo "Henter Bluetoothfra $NAME ($DEVICE)..."
  adb -s $DEVICE shell "ls $BT_DIR/*.*" 2>&1 | while read -r file; do
    adb -s $DEVICE pull "$file" "$LOCAL_BT_DIR/" 2>&1
  done
  echo "Bluetooth hentet fra $NAME ($DEVICE)"
  
  echo "------------------------------------------------------------------------------------"
}


# Funksjon for å håndtere en enhet ved å hente ID og navn fra get_device_info
function process_device {
  local device_name=$1
  local info=($(get_device_info "$device_name"))
  local DEVICE="${info[1]}"  # Hent enhetens ID fra get_device_info

  if sjekk_enhets_tilkobling $device_name $DEVICE; then
    pull_packetdumps $device_name $DEVICE  # Passerer device_name og device_id
  else
    echo "Hopper over $device_name ($DEVICE) da enheten ikke er tilgjengelig."
  fi
}

# Hovedlogikk for å håndtere en spesifikk enhet eller alle enheter
device_name=$2

if [[ "$device_name" == "ALLE" ]]; then
  echo "Kjører operasjonene på alle enheter."
  for device_name in ${(k)device_info_map}; do
    process_device $device_name
  done
else
  process_device $device_name
fi

echo "Alle pakkedumpfiler er hentet fra alle enhetene."
