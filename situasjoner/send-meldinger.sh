#!/usr/bin/env zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map
source "$BASE_DIR/../ressurser/felles.sh"

# Definer variabler for touch-posisjoner
X_CENTER=50          # Midt på skjermen
Y_7_PERCENT_UP=93   # 7% opp fra bunnen
Y_60_PERCENT_DOWN=60  # 60% ned fra toppen
Y_15_PERCENT_UP=85  # 15% opp fra bunnen

LANGUAGE=${1:-en}

# Sjekk at språkparameter er enten 'en' eller 'no'
if [[ "$LANGUAGE" != "en" && "$LANGUAGE" != "no" ]]; then
  echo "Ugyldig språk. Bruk 'en' eller 'no'."
  exit 1
fi

# Sett SOURCE_PATH til riktig mappe basert på språk
SOURCE_PATH=$(realpath "./Datasett/meldinger/$LANGUAGE")

# Sjekk om situasjonsnummer er angitt
if [ -z "$2" ]; then
  echo "Bruk: $0 <situasjonsnummer> [en|no]"
  exit 1
fi

SITUASJON="$2"

# Sjekk om kildekatalogen for meldinger finnes
if [ ! -d "$SOURCE_PATH" ]; then
  echo "Kildekatalogen $SOURCE_PATH finnes ikke."
  exit 1
fi

# Hent filene som matcher situasjonsnummeret
#FILES=($(find "$SOURCE_PATH" -type f -name "${SITUASJON}_*.txt" | sort -t'_' -k3,3n)) # Sorter numerisk stigende basert på det tredje feltet
FILES=($(find "$SOURCE_PATH" -type f -name "${SITUASJON}_*.txt" | sort -t'_' -k3,3n -k4,4n))

# Sjekk om vi har noen filer
if [ ${#FILES[@]} -eq 0 ];then
  echo "Ingen filer funnet for situasjon $SITUASJON."
  exit 1
fi

echo "Fant følgende filer for situasjon $SITUASJON i $LANGUAGE:"

file_count=0
for FILE in "${FILES[@]}"; do
  echo "$FILE"
  ((file_count++))
done

echo "Antall meldinger funnet: $file_count"

echo ""

# Assosiativ array for å holde styr på første melding per avsender
typeset -A first_message_sent

# Variabel for å holde styr på forrige avsender
previous_sender=""

# Variabel for å holde styr på om første melding i situasjon 7 er sendt
first_message_situasjon_7=true

# Funksjon for å kommunisere med mobiltelefon via adb
function adb_send_message {
  local device=$1
  local message_content=$2
  local confirmation="n"

  while [[ "$confirmation" != "y" ]]; do
      # Send meldingen
      adb -s $device shell input text "$message_content"

      # Gi  muligheten til å bekrefte om meldingen ble riktig
      echo ""
      echo -e "$RED BLE DET LIMT INN RIKTIG? Trykk y/ENTER for 'ja, send!', eller trykk n for å prøve igjen (y/n) $RESET"

      # Les brukerinput med timeout på 3 sekunder
      read -t 3 -r confirmation
      exit_code=$?  # Fanger resultatet fra read

      if [[ $exit_code -ne 0 ]]; then
          confirmation="y"
      fi

      confirmation=${confirmation:-y}  # Sett standardverdi til "y" hvis ENTER trykkes uten input

      # Hvis brukeren svarer "n", gi beskjed og prøv på nytt
      if [[ "$confirmation" == "n" ]]; then
        echo "Prøver å lime inn meldingen på nytt på $avsender sin $device..."
      fi
  done

  # Når meldingen er riktig, naviger og send meldingen
  adb -s $device shell input keyevent 61  # TAB (for å navigere videre til send-knappen)
  adb -s $device shell input keyevent 66  # ENTER (for å sende meldingen)
}


function check_sender_and_pause {
  local CURRENT_SENDER=$1
  if [[ "$previous_sender" == "$CURRENT_SENDER" ]]; then
    echo -e "\e[33mSamme avsender ($CURRENT_SENDER) som forrige melding, venter 2 sekunder.\e[0m"
    sleep 2
  fi
  previous_sender="$CURRENT_SENDER"  # Oppdater forrige avsender
}


function spesielle_meldinger_etter {
  local avsender=$1
  local device=$2
  local message_content=$3


  # Situasjon 5, melding nr.6
  if [[ "$message_content" =~ ^Interesting\ feature.*#NTNU-MISEB.*$ ]] && [[ "$avsender" == "Alice" ]]; then
      echo "$avsender sender 'Interesting feature...#NTNU-MISEB...' og har til hensikt å reveale Dave i gruppa eller legge Dave til som kontakt? Sover i en stund i tilfellet operatør kan utføre dette for Alice/Dave!" >&2
      sleep 10
  fi


  # Situasjon 6, melding nr.6
  if [[ "$message_content" =~ ^gtg!\ #NTNU-MISEB.*$ ]] && [[ "$avsender" == "Alice" ]]; then
    echo "$avsender ($device) sender 'gtg! #NTNU-MISEB'. Slår av Bluetooth og WiFi for $avsender." >&2

    fra_samtale_til_burger "$device"

    toggle_kanal "$avsender" "Bluetooth" # avsender=Alice
    
    sleep 3
    
    toggle_kanal "$avsender" "WiFi" # avsender=Alice

    tilbake_til_forumet "$device" # avsender=Alice, device=41131JEHN09843

    echo "Bluetooth og WiFi er slått av for $avsender. Går tilbake til forum-kanalen." >&2

    sleep 5
  fi
  

  # Situasjon 6, melding nr.8
  if [[ "$message_content" =~ ^Yep\ #NTNU-MISEB.*$ ]] && [[ "$avsender" == "Dave" ]]; then
    echo "$avsender sender 'Yep #NTNU-MISEB'. Slår på Bluetooth og WiFi for Alice." >&2

    local alice_id=$(hent_enhets_id "Alice") || return 1

    fra_samtale_til_burger "$alice_id"

    toggle_kanal "Alice" "Bluetooth" # avsender=Dave
    
    sleep 3
    
    toggle_kanal "Alice" "WiFi" # avsender=Dave
    
    sleep 3

    tilbake_til_forumet "$alice_id" # avsender=Dave, device=emulator-5554

    sleep 5
  fi

}

# Funksjon for å lese meldingsinnholdet fra fil
function get_message_content {
  local filename=$1

  # Les meldingsinnholdet fra filen
  local message_content=$(cat "$filename")
  
  # Returner meldingsinnholdet som variabel
  echo "$message_content"
}

function prep_message_content {
  local message_content=$1

  # Escape mellomrom, apostrof, spørsmålstegn og parenteser
  escaped_message=$(echo "$message_content" | sed "s/ /%s/g; s/'/\\\\'/g; s/?/\\\\?/g; s/(/\\\\(/g; s/)/\\\\)/g")
  echo "$escaped_message"
}

function handle_situasjon_1_3 {
  local device=$1
  local avsender=$2
  if [[ -z "${first_message_sent[$avsender]}" ]]; then
      tap_screen_prosent "$device" $X_CENTER $Y_7_PERCENT_UP
      first_message_sent[$avsender]=true
  else
      tap_screen_prosent "$device" $X_CENTER $Y_60_PERCENT_DOWN
  fi
}

function handle_situasjon_4_5 {
    local device=$1
    tap_screen_prosent "$device" $X_CENTER $Y_7_PERCENT_UP
}

function handle_situasjon_6 {
    local DEVICE=$1
    tap_screen_prosent "$DEVICE" $X_CENTER $Y_7_PERCENT_UP
}

function handle_situasjon_7 {
  local device=$1
  local avsender=$2
  local message_number=$3

  if [[ $message_number -eq 1 ]]; then
    adb -s $device shell su -c "kill -2 \$(cat \$(ls -t $TOR_DIR/*-tcpdump.pid | head -n 1))"
    #adb -s $device shell su -c "rm \$(ls -t $TOR_DIR/*.pcapng | head -n 1)"
  fi

  if [[ $message_number -eq 5 ]]; then
    echo "Starter ekstra pakkedump for $avsender ($device)..." >&2
    set --
    export SOURCED_MODE=1
    source "$BASE_DIR/../SendMeldinger/Pakkedump/styr-opptak.sh"
    start_tor_tcpdump $device $avsender "Tor" 2>&1 # Funksjonen starter tcpdump i bakgrunnen

    echo "$avsender sender 'I wonder if anyone...#NTNU-MISEB...'. Slår av Bluetooth og WiFi for ${YELLOW}$avsender${RED}. Slår på Tor for $avsender. ${GREEN} GÅR TILBAKE TIL BLOGGSKRIVING NÅR KLAR ${RESET} " >&2

    local alice_id=$(hent_enhets_id "Alice") || return 1

    fra_samtale_til_burger "$alice_id"

    toggle_kanal $avsender "Bluetooth" # avsender=Alice
    
    sleep 3
    
    toggle_kanal $avsender "WiFi" # avsender=Alice
    
    sleep 3

    toggle_kanal $avsender "Tor" # avsender=Alice
    
    sleep 3

    tilbake_til_blogg "$alice_id" # avsender=Alice, device=41131JEHN09843

    sleep 10
  fi

  if [[ $message_number -eq 9 ]]; then
    echo "$avsender ($device) sender 'Tor is a great...#NTNU-MISEB...'. Slår på Bluetooth og WiFi for Alice og ${GREEN}venter litt før deaktivering av Tor. ${RESET} " >&2

    local alice_id=$(hent_enhets_id "Alice") || return 1

    fra_samtale_til_burger "$alice_id"

    toggle_kanal "Alice" "Bluetooth" # avsender=Charlie
    
    sleep 20
    
    toggle_kanal "Alice" "WiFi" # avsender=Charlie
    
    sleep 20

    toggle_kanal "Alice" "Tor" # avsender=Charlie
    
    sleep 20

    tilbake_til_blogg $alice_id # avsender=Charlie, device=34061FDH2003BL

    sleep 15

    latest_pid_file=$(adb -s $alice_id shell su -c "ls -t $TOR_DIR/*-tcpdump.pid | head -n 1")
    echo "Leter etter siste PID-fil: $latest_pid_file" >&2
    # Dreper siste Tor tcpdump-prosessen på Alice
    adb -s $alice_id shell su -c "kill -2 \$(cat \$(ls -t $TOR_DIR/*-tcpdump.pid | head -n 1))"
  
  fi

  device=$(hent_enhets_id $avsender) || return 1
  echo -e "$RED *** STOPP! *** Gjør klar siste bloggpost, men IKKE TRYKK I skrivefeltet på ${YELLOW}$avsender ($device)${RED} før du fortsetter. ${GREEN}Trykk ENTER for å skrive og sende. ${RESET}" >&2
  read -r

  if [[ $first_message_situasjon_7 == true ]]; then
      first_message_situasjon_7=false
  else
      tap_screen_prosent $device $X_CENTER $Y_15_PERCENT_UP
  fi
}

function check_situasjon_and_handle {
  local situasjons_nummer=$1
  local device=$2
  local avsender=$3
  local message_number=$4

  case "$situasjons_nummer" in
      1|2|3)
          handle_situasjon_1_3 "$device" "$avsender"
          ;;
      4|5)
          handle_situasjon_4_5 "$device"
          ;;
      6)
          handle_situasjon_6 "$device"
          ;;
      7)
          handle_situasjon_7 "$device" "$avsender" $message_number
          ;;
  esac
}


# Hovedloop gjennom alle filene
for FILE in "${FILES[@]}"; do
  filename=$(basename "$FILE")

  # Ekstrakt de nødvendige feltene fra filnavnet
  #read situasjons_nummer kanal message_number avsender mottaker <<< $(extract_fields_from_filename "$filename")
  read situasjons_nummer kanal message_number avsender mottaker < <(extract_fields_from_filename "$filename")

  # Finn riktig enhet basert på avsenderen fra device_map (som er definert i felles.sh)
  local info=($(get_device_info "$avsender"))
  local device="${info[1]}"

  if [ -z "$device" ]; then
    echo "Fant ingen enhet for $avsender. Hopper over."
    continue
  fi

  # Pause 2s hvis nødvendig
  check_sender_and_pause "$avsender"

  echo "Melding #$message_number fra $avsender til $mottaker på enhet $device"

  # Henter melding fra fil
  message_content=$(get_message_content "$FILE")
  echo "Melding ${YELLOW}$message_number${RESET}: ${GREEN}"$message_content"${RESET}" >&2

  # Kanseller spesialtegn i meldinger
  escaped_message=$(prep_message_content "$message_content")

  # Distribuer til riktig funksjon basert på situasjon
  check_situasjon_and_handle $situasjons_nummer $device $avsender "$message_number"

  # Sender meldingen via adb
  lagre_tor_sockets $device

  adb_send_message $device "$escaped_message"

  spesielle_meldinger_etter $avsender $device "$message_content"

done


echo "Alle meldinger sendt."
