#!/usr/bin/env zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map
source "$BASE_DIR/../../ressurser/felles.sh"

LOCAL_PACKETDUMP_DIR=./pakkedumper
DRY_RUN=false

# Funksjon for å vise riktig bruk av skriptet
function print_usage {
  echo "Feil: Du må angi riktig bruk."
  echo "Bruk: $0 <lokal|enhet> <Alice|Bob|Charlie|Dave|ALLE> <wifi|bt|tor|ALLE> [dato] [dry-run]"
  exit 1
}

# Funksjon for å validere alle input-parametere
function validate_inputs {
  if [ -z "$1" ]; then
    print_usage
  fi

  if [[ "$2" != "Alice" && "$2" != "Bob" && "$2" != "Charlie" && "$2" != "Dave" && "$2" != "ALLE" ]]; then
    print_usage
  fi

  if [[ "$3" != "wifi" && "$3" != "bt" && "$3" != "tor" && "$3" != "ALLE" ]]; then
    print_usage
  fi
}

# Funksjon for å sjekke om enheten er online før sletting
function sjekk_enhets_tilkobling {
  local DEVICE=$1
  if ! adb -s $DEVICE get-state 1>/dev/null 2>/dev/null; then
    echo "Enheten $DEVICE er ikke tilgjengelig eller ikke koblet til."
    return 1  # Returner feil hvis enheten ikke er tilgjengelig
  fi
  return 0
}

# Funksjon for å be om bekreftelse før sletting
function confirm_deletion {
  local PATH=$1
  echo "Er du sikker på at du vil slette filer i $PATH? (ja/nei)"
  read answer
  if [[ "$answer" != "ja" ]]; then
    echo "Sletting avbrutt for $PATH."
    return 1
  fi
  return 0
}

# Funksjon for å fjerne pakkedumpfiler fra Android-enhetene
function purge_device_packetdumps {
  local USER=$1
  local TYPE=$2  # Type kan være 'wifi', 'bt', 'tor' eller 'ALLE'
  local DATE_FILTER=$3  # Valgfri dato
  local USERS_TO_PROCESS

  if [[ "$USER" == "ALLE" ]]; then
    USERS_TO_PROCESS=(${(k)device_info_map})  # Hvis ALLE er angitt, slett for alle brukere
  else
    USERS_TO_PROCESS=($USER)  # Velg spesifikk bruker
  fi

  for NAME in $USERS_TO_PROCESS; do
    info=($(get_device_info "$NAME"))
    DEVICE="${info[1]}"  # Hent enhetens ID fra get_device_info

    if sjekk_enhets_tilkobling $DEVICE; then
      if [ -z "$DATE_FILTER" ];then
        echo "Ingen dato angitt. Fjerner alle pakkedumpfiler på enhet $NAME ($DEVICE)"
      else
        echo "Fjerner pakkedumpfiler fra $NAME ($DEVICE) med dato $DATE_FILTER"
      fi

      if [[ "$DRY_RUN" == true ]]; then
        echo "[Dry run] Dette ville slette WiFi-, BT- og Tor-pakkedumper på $DEVICE for $NAME"
      else
        # Håndter sletting basert på type (wifi, bt, tor eller ALLE)
        if [[ "$TYPE" == "wifi" || "$TYPE" == "ALLE" ]]; then
          echo "Prøver å finne WiFi-pakkedumpfiler for $NAME på $DEVICE"
          WIFI_PATH="$WIFI_DIR"
          adb -s $DEVICE shell "find $WIFI_PATH -name '${DATE_FILTER}*.*' -delete"
        fi

        if [[ "$TYPE" == "bt" || "$TYPE" == "ALLE" ]]; then
          echo "Prøver å finne Bluetooth-pakkedumpfiler for $NAME på $DEVICE"
          BT_PATH="$BT_DIR"
          adb -s $DEVICE shell "find $BT_PATH -name '${DATE_FILTER}*.*' -delete"
        fi

        if [[ "$TYPE" == "tor" || "$TYPE" == "ALLE" ]]; then
          echo "Prøver å finne Tor-pakkedumpfiler for $NAME på $DEVICE"
          TOR_PATH="$TOR_DIR"
          adb -s $DEVICE shell "find $TOR_PATH -name '${DATE_FILTER}*.*' -delete"
        fi
      fi
    else
      echo "Hopper over $NAME da enheten ikke er online."
    fi

    echo "--------------------------------------------------------------------------------"
  done
}

# Funksjon for å fjerne pakkedumpfiler lokalt
function purge_local_packetdumps {
  local USER=$1
  local TYPE=$2  # Type kan være 'wifi', 'bt', 'tor' eller 'ALLE'
  local DATE_FILTER=$3  # Valgfri dato
  local USERS_TO_PROCESS

  if [[ "$USER" == "ALLE" ]]; then
    USERS_TO_PROCESS=(${(k)device_info_map})  # Hvis ALLE er angitt, slett for alle brukere
  else
    USERS_TO_PROCESS=($USER)  # Velg spesifikk bruker
  fi

  for NAME in $USERS_TO_PROCESS; do

    LOCAL_WIFI_DIR="${LOCAL_PACKETDUMP_DIR}/${NAME}/wifi"
    LOCAL_TOR_DIR="${LOCAL_PACKETDUMP_DIR}/${NAME}/tor"
    LOCAL_BT_DIR="${LOCAL_PACKETDUMP_DIR}/${NAME}/bt"

    if [[ ! -d "$LOCAL_WIFI_DIR" && ! -d "$LOCAL_BT_DIR" && ! -d "$LOCAL_TOR_DIR" ]]; then
      echo "Advarsel: Ingen lokale kataloger funnet for $NAME. Hopper over."
      continue
    fi

    if [ -z "$DATE_FILTER" ]; then
      echo "Ingen dato angitt. Fjerner alle lokale pakkedumpfiler for $NAME"
    else
      echo "Fjerner lokale pakkedumpfiler for $NAME med dato $DATE_FILTER"
    fi

    if [[ "$DRY_RUN" == true ]]; then
      echo "[Dry run] Dette ville slette lokale WiFi-, BT- og Tor-pakkedumper for $NAME"
    else
      # Håndter sletting basert på type (wifi, bt, tor eller ALLE)
      if [[ "$TYPE" == "wifi" || "$TYPE" == "ALLE" ]]; then
        confirm_deletion "$LOCAL_WIFI_DIR" || continue
        echo "Sletter WiFi-pakkedumpfiler for $NAME"
        find "$LOCAL_WIFI_DIR" -name "${DATE_FILTER}*.*" -delete
      fi

      if [[ "$TYPE" == "bt" || "$TYPE" == "ALLE" ]]; then
        confirm_deletion "$LOCAL_BT_DIR" || continue
        echo "Sletter Bluetooth-pakkedumpfiler for $NAME"
        find "$LOCAL_BT_DIR" -name "${DATE_FILTER}*.*" -delete
      fi

      if [[ "$TYPE" == "tor" || "$TYPE" == "ALLE" ]]; then
        confirm_deletion "$LOCAL_TOR_DIR" || continue
        echo "Sletter Tor-pakkedumpfiler for $NAME"
        find "$LOCAL_TOR_DIR" -name "${DATE_FILTER}*.*' -delete"
      fi
    fi

    echo "--------------------------------------------------------------------------------"
  done
}

# Funksjon for å utføre slettingen basert på input
function execute_deletion {
  local location=$1  # enten 'enhet' eller 'lokal'
  local user=$2
  local type=$3  # 'wifi', 'bt', 'tor' eller 'ALLE'
  local date_filter=$4  # Valgfri dato

  if [[ "$location" == "enhet" ]]; then
    purge_device_packetdumps $user $type $date_filter
  elif [[ "$location" == "lokal" ]]; then
    purge_local_packetdumps $user $type $date_filter
  else
    print_usage
  fi
}

# Hovedlogikk for å håndtere en spesifikk enhet eller alle enheter
location=$1
device_name=$2
type=$3
date_filter=$4
dry_run_param=$5 

if [[ "$dry_run_param" == "dry-run" ]]; then
  DRY_RUN=true
fi

if [[ "$location" != "enhet" && "$location" != "lokal" ]]; then
  echo "Ugyldig argument: Bruk enten 'enhet' eller 'lokal'"
  exit 1
fi

# Kjør validering av input-parametere
validate_inputs $location $device_name $type

# Utfør sletting basert på validerte input-parametere
execute_deletion $location $device_name $type $date_filter

echo "Pakkedumpfjerning er fullført."
