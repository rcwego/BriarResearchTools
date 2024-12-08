#!/usr/bin/env zsh
echo "DEBUG: Arguments received: $@"

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map
source "$BASE_DIR/../../ressurser/felles.sh"

# Funksjon for å opprette kataloger for WiFi og Bluetooth dump
function create_dump_dirs {
  local DEVICE=$1
  local device_name=$2
  echo "Oppretter kataloger for WiFi og Bluetooth dump på enhet $device_name ($DEVICE)"
  adb -s $DEVICE shell "mkdir -p $WIFI_DIR"
  adb -s $DEVICE shell "mkdir -p $BT_DIR"
}

function start_tor_tcpdump {
  local DEVICE=$1
  local device_name=$2
  local kanal=$3
  TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)  # Lager ISO 8601-tidsstempel
  TOR_BASE_FILE_NAME="${TOR_DIR}/${TIMESTAMP}-${device_name}"
  WLAN0_PCAP_FILE_NAME="$TOR_BASE_FILE_NAME-wlan0.pcapng"
  WLAN0_IP_FILE_NAME="$TOR_BASE_FILE_NAME-wlan0-ip.txt"
  WLAN0_MAC_FILE_NAME="$TOR_BASE_FILE_NAME-wlan0-mac.txt"
  TOR_TRUE="$TOR_BASE_FILE_NAME-is-$kanal.txt"
  TOR_SOCKETS_FILE_NAME="$TOR_BASE_FILE_NAME-$kanal-sockets.txt"
  TCPDUMP_PID_FILE="$TOR_BASE_FILE_NAME-tcpdump.pid"  # Fil for å lagre PID


  echo "Starter $kanal pakkedump på enhet $device_name ($DEVICE)"

  adb -s $DEVICE shell su -c "mkdir -p $TOR_DIR"
  adb -s $DEVICE shell su -c "echo 1 > $TOR_TRUE"
  adb -s $DEVICE shell su -c "netstat -tunp | grep tor > $TOR_SOCKETS_FILE_NAME"

  skru_av_ipv6 $DEVICE

  # Finn IP-adresse og MAC-adresse for wlan0-grensesnittet
  adb -s $DEVICE shell su -c "ip -f inet addr show wlan0 | grep inet | awk '{print \$2}' | cut -d/ -f1 > $WLAN0_IP_FILE_NAME"
  adb -s $DEVICE shell su -c "cat /sys/class/net/wlan0/address > $WLAN0_MAC_FILE_NAME"

  # Kjør tcpdump som root og lagre filen på enheten
  adb -s $DEVICE shell su -c "tcpdump -i any -p -s 0 -w $WLAN0_PCAP_FILE_NAME -U" &
  sleep 1
  #adb -s $DEVICE shell su -c "ps -eo pid,etime,args | grep 'tcpdump -i any -p -s 0 -w $WLAN0_PCAP_FILE_NAME -U' | grep -v su | grep -v magisk | grep -v grep > $TCPDUMP_PID_FILE-full"
  adb -s $DEVICE shell su -c "ps -eo pid,etime,args | grep 'tcpdump -i any -p -s 0 -w $WLAN0_PCAP_FILE_NAME -U' | grep -v su | grep -v magisk | grep -v grep | awk '{print \$1}' > $TCPDUMP_PID_FILE"

}

# Funksjon for å starte tcpdump på WiFi-grensesnitt
function start_wifi_tcpdump {
  local DEVICE=$1
  local device_name=$2
  local kanal=$3
  TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)  # Lager ISO 8601-tidsstempel
  WIFI_BASE_FILE_NAME="${WIFI_DIR}/${TIMESTAMP}-${device_name}"
  WLAN0_PCAP_FILE_NAME="$WIFI_BASE_FILE_NAME-wlan0.pcapng"
  WLAN0_IP_FILE_NAME="$WIFI_BASE_FILE_NAME-wlan0-ip.txt"
  WLAN0_MAC_FILE_NAME="$WIFI_BASE_FILE_NAME-wlan0-mac.txt"
  WIFI_TRUE="$WIFI_BASE_FILE_NAME-is-$kanal.txt"
  TCPDUMP_PID_FILE="$WIFI_BASE_FILE_NAME-tcpdump.pid"  # Fil for å lagre PID


  echo "Starter $kanal pakkedump på enhet $device_name ($DEVICE)"

  adb -s $DEVICE shell su -c "echo 1 > $WIFI_TRUE"  # Sett flagg for WiFi

  skru_av_ipv6 $DEVICE

  # Finn IP-adresse og MAC-adresse for wlan0-grensesnittet
  adb -s $DEVICE shell su -c "ip -f inet addr show wlan0 | grep inet | awk '{print \$2}' | cut -d/ -f1 > $WLAN0_IP_FILE_NAME"
  adb -s $DEVICE shell su -c "cat /sys/class/net/wlan0/address > $WLAN0_MAC_FILE_NAME"

  # Kjør tcpdump som root og lagre filen på enheten
  adb -s $DEVICE shell su -c "tcpdump -i any -p -s 0 -w $WLAN0_PCAP_FILE_NAME -U" &
  sleep 0.5
  #adb -s $DEVICE shell su -c "ps -eo pid,etime,args | grep 'tcpdump -i any -p -s 0 -w $WLAN0_PCAP_FILE_NAME -U' | grep -v su | grep -v magisk | grep -v grep > $TCPDUMP_PID_FILE-full"
  adb -s $DEVICE shell su -c "ps -eo pid,etime,args | grep 'tcpdump -i any -p -s 0 -w $WLAN0_PCAP_FILE_NAME -U' | grep -v su | grep -v magisk | grep -v grep | awk '{print \$1}' > $TCPDUMP_PID_FILE"
}

# Funksjon for å starte Bluetooth-pakkedumping
function start_bt_dump {
  local DEVICE=$1
  local device_name=$2
  local kanal=$3
  TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)
  BT_BASE_FILE_NAME="${BT_DIR}/${TIMESTAMP}-${device_name}"
  BT_TRUE="$BT_BASE_FILE_NAME-is-bt.txt"

  echo "Starter $kanal pakkedump på enhet $device_name ($DEVICE)"
    
  # Aktiver hci-log
  # adb -s $DEVICE shell su -c "settings get global bluetooth_hci_log"
  # adb -s $DEVICE shell su -c "settings get secure bluetooth_hci_log"
  adb -s $DEVICE shell su -c "settings put secure bluetooth_name $device_name"
  adb -s $DEVICE shell su -c "settings put global bluetooth_hci_log 1"
  adb -s $DEVICE shell su -c "settings put secure bluetooth_hci_log 1"
  adb -s $DEVICE shell su -c "svc bluetooth disable"  # Slå av Bluetooth
  adb -s $DEVICE shell su -c "svc bluetooth enable"   # Slå på Bluetooth
  sleep 3

  while ! adb -s "$DEVICE" shell su -c "ls -lha $BT_LOG_SOURCE" > /dev/null 2>&1; do
    echo -e "${RED}*** STOPP! *** Blåtann-loggen er ikke tilgjengelig på $device_name sin $DEVICE.${RESET}"
    
    echo "Aktiver BT HCI snoop log i Developer options i GUI."
    #echo "Trykk 's' for å hoppe over til neste enhet, eller trykk ENTER for å prøve igjen."
    #read user_input

    if [[ "$user_input" == "s" ]]; then
      echo "Hopper over $device_name ($DEVICE) og går videre."
      break
    fi

    adb -s $DEVICE shell su -c "svc bluetooth disable"
    adb -s $DEVICE shell su -c "svc bluetooth enable"
    echo "Prøver på nytt om 5 sekund..."
    sleep 5
  done

  if adb -s "$DEVICE" shell su -c "ls -lha $BT_LOG_SOURCE" > /dev/null 2>&1; then
    echo -e "${GREEN}Blåtann dump aktivert på $device_name ($DEVICE)!${RESET}"
    adb -s $DEVICE shell su -c "echo 1 > $BT_TRUE"
  fi
}

function stop_wifi_capture {
  local DEVICE=$1
  local device_name=$2
  local kanal=$3

  echo "Stopper $kanal pakkedump på enhet $device_name ($DEVICE)"
  
  # Stopp alle tcpdump-instanser
  adb -s $DEVICE shell su -c "killall -2 tcpdump" 2>&1 #adb -s $DEVICE shell su -c "pkill -f tcpdump"
  echo "Alle tcpdump-instanser stoppet på $device_name ($DEVICE)"
}


function stop_bt_capture {
  local DEVICE=$1
  local device_name=$2
  local kanal=$3

  TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)
  BT_BASE_FILE_NAME="${BT_DIR}/${TIMESTAMP}-${device_name}"
  BT_FILE_NAME="$BT_BASE_FILE_NAME-bt.log"
  BT_MAC_FILE_NAME="$BT_BASE_FILE_NAME-bt-mac.txt"

  echo "Stopper $kanal pakkedump på enhet $device_name ($DEVICE)"
  echo "Stopper alle btmon-instansene på enhet $device_name ($DEVICE). DU MÅ SKRU AV SELV!"
  
  # Hent hci-log
  #adb -s $DEVICE shell su -c "ls -lha $BT_LOG_SOURCE"
  adb -s $DEVICE shell su -c "cp $BT_LOG_SOURCE $BT_FILE_NAME"

  adb -s $DEVICE shell su -c "settings get secure bluetooth_address > /data/local/tmp/bluetooth_address.txt"
  adb -s $DEVICE shell su -c "mv /data/local/tmp/bluetooth_address.txt $BT_MAC_FILE_NAME"

  # Deaktiver hci-log
  adb -s $DEVICE shell su -c "settings put global bluetooth_hci_log 0"
  adb -s $DEVICE shell su -c "settings put secure bluetooth_hci_log 0"
  adb -s $DEVICE shell su -c "svc bluetooth disable"  # Slå av Bluetooth
  adb -s $DEVICE shell su -c "svc bluetooth enable"   # Slå på Bluetooth
}


# Funksjon for å kjøre operasjonene for en gitt enhet
function process_device {
  local device_name=$1
  local info=($(get_device_info "$device_name"))
  local DEVICE="${info[1]}"  # Hent enhetens ID fra get_device_info

  if sjekk_enhets_tilkobling $device_name $DEVICE; then
    stop_capture $DEVICE $device_name
  else
    echo "Hopper over $device_name ($DEVICE) da enheten ikke er tilgjengelig."
  fi
}

# Funksjon for å kjøre start-operasjoner på en enhet
function start_device_capture {
  local device_name=$1
  local kanal=$2
  local info=($(get_device_info "$device_name"))
  local DEVICE="${info[1]}"  # Hent enhetens ID fra get_device_info

  if sjekk_enhets_tilkobling $device_name $DEVICE; then
    set_device_hostname $device_name
    create_dump_dirs $DEVICE $device_name

    if [ "$kanal" = "Tor" ]; then
        start_tor_tcpdump $DEVICE $device_name $kanal
    
    elif [ "$kanal" = "wifi" ] || [ "$kanal" = "WiFi" ]; then
        start_wifi_tcpdump $DEVICE $device_name $kanal

    elif [ "$kanal" = "bt" ] || [ "$kanal" = "Bluetooth" ]; then
        start_bt_dump $DEVICE $device_name
    fi

  else
    echo "Hopper over $device_name ($DEVICE) da enheten ikke er tilgjengelig."
  fi
}

# Funksjon for å kjøre stopp-operasjoner på en enhet
function stop_device_capture {
  local device_name=$1
  local kanal=$2
  local info=($(get_device_info "$device_name"))
  local DEVICE="${info[1]}"  # Hent enhetens ID fra get_device_info

  if sjekk_enhets_tilkobling $device_name $DEVICE; then
    
    if [ "$kanal" = "Tor" ] || [ "$kanal" = "wifi" ] || [ "$kanal" = "WiFi" ]; then
        stop_wifi_capture $DEVICE $device_name
    
    elif [ "$kanal" = "bt" ] || [ "$kanal" = "Bluetooth" ]; then
        stop_bt_capture $DEVICE $device_name
    fi

  else
    echo "Hopper over $device_name ($DEVICE) da enheten ikke er tilgjengelig."
  fi
}

# Sjekk om skriptet er kjørt direkte eller sourcet
# if [[ "${(%):-%N}" != "$0" ]]; then
if [[ -z "${SOURCED_MODE}" ]]; then
  echo "Skriptet er IKKE sourcet."

  # Hovedlogikk for å håndtere en spesifikk enhet eller alle enheter
  action=$1
  device_name=$2
  kanal=$3

  if [[ "$action" != "start" && "$action" != "stopp" ]]; then
    echo "Ugyldig argument: Bruk enten 'start' eller 'stopp'"
    exit 1
  fi

  if [[ "$device_name" == "ALLE" ]]; then
    echo "Kjører operasjonene på alle enheter."
    for device_name in ${(k)device_info_map}; do
      if [[ "$action" == "start" ]]; then
        start_device_capture $device_name $kanal
      elif [[ "$action" == "stopp" ]]; then
        stop_device_capture $device_name $kanal
      fi
    done
  else
    if [[ "$action" == "start" ]]; then
      start_device_capture $device_name $kanal
    elif [[ "$action" == "stopp" ]]; then
      stop_device_capture $device_name $kanal
    fi
  fi

  echo "Pakkedumping er: '$action' for $kanal på $2"

else
  echo "Skriptet er sourcet."
fi