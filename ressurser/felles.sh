#!/bin/zsh

# Finn absolutt sti til felles.sh
BASE_DIR=$(dirname "$(realpath "$0")")

# Eksterne tjenere
EKSTERN_1=192.168.1.1
EKSTERN_2=192.168.1.2

# Stier til pakkedump
LOKALLAGRING_DIR="/sdcard/Documents/lokallagring"
PAKKEDUMP_DIR="/sdcard/Documents/pakkedump"
WIFI_DIR="${PAKKEDUMP_DIR}/wifi"
TOR_DIR="${PAKKEDUMP_DIR}/tor"
BT_DIR="${PAKKEDUMP_DIR}/bt"

# BT Log source på Android API 34 Google Pixel 7(a)
BT_LOG_SOURCE="/data/misc/bluetooth/logs/btsnoop_hci.log"

# BRIAR lagringssti
BRIAR_LAGRINGSSTI="/data/data/org.briarproject.briar.android"

# Definer fargevariabler
RESET="\e[0m"
GREEN="\e[32m"
BOLD_GREEN="\e[1;32m"
YELLOW="\e[33m"
BOLD_YELLOW="\e[1;33m"
RED="\e[31m"
BOLD_RED="\e[1;31m"

# Les enhets-ID-er, passord, passordstyrke og type fra enheter.conf
typeset -A device_info_map

# Funksjon for å hente enhetstype basert på enhetsnavn
get_device_arkitektur() {
    local device_name=$1
    local info=($(get_device_info "$device_name"))
    local device_type="${info[4]}"  # Hent type fra info

    if [ "$device_type" = "ekstern-1" ] || [ "$device_type" = "ekstern-2" ]; then
        echo "x8664"
    elif [ "$device_type" = "lokal" ] || [ "$device_type" = "fysisk" ]; then
        echo "arm64"
    else
        echo "ukjent arkitektur"
    fi
}

function extract_fields_from_filename {
  local filename=$1
  local situasjons_nummer=$(echo "$filename" | cut -d'_' -f1)
  local kanal=$(echo "$filename" | cut -d'_' -f2)
  local message_number=$(echo "$filename" | cut -d'_' -f3)
  local avsender=$(echo "$filename" | cut -d'_' -f4)
  local mottaker=$(echo "$filename" | cut -d'_' -f5 | cut -d'.' -f1)  # Fjern .txt
  
  echo "$situasjons_nummer $kanal $message_number $avsender $mottaker"
}

# Funksjon for å oppdatere mediescanner for en gitt katalog
function update_media_scanner {
  local DEVICE=$1
  local DIR=$2
  echo "Oppdaterer mediescanner for $DIR på enhet $DEVICE..."
  adb -s $DEVICE shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://$DIR
  echo "Mediescanner oppdatert for enhet $DEVICE"
}

function show_directory_contents {
  local DEVICE=$1
  echo "Innhold i destinasjonskatalogen på enhet $DEVICE:"
  adb -s $DEVICE shell "ls -l $MESSAGES_DIR"
}

function ensure_directory_exists {
  local DEVICE=$1
  echo "Sørger for at $MESSAGES_DIR eksisterer på enhet $DEVICE..."
  adb -s $DEVICE shell "mkdir -p $MESSAGES_DIR"
}

# Funksjon for å telle meldinger i meldingsmappen for hver enhet
function count_messages() {
  for NAME in ${(k)device_map}; do  # Itererer over nøklene i assosiativ array i Zsh
    DEVICE=${device_map[$NAME]}
    echo "Teller meldinger for enhet: $DEVICE ($NAME)"
    
    # Teller meldinger i meldinger/no
    if adb -s $DEVICE shell "[ -d $MESSAGES_DIR/no ]"; then
      NO_COUNT=$(adb -s $DEVICE shell "ls -1 $MESSAGES_DIR/no | wc -l")
      echo "Antall meldinger på norsk (no): $NO_COUNT"
    else
      echo "Ingen meldinger på norsk (no) på enhet $DEVICE ($NAME)."
    fi
    
    # Teller meldinger i meldinger/en
    if adb -s $DEVICE shell "[ -d $MESSAGES_DIR/en ]"; then
      EN_COUNT=$(adb -s $DEVICE shell "ls -1 $MESSAGES_DIR/en | wc -l")
      echo "Antall meldinger på engelsk (en): $EN_COUNT"
    else
      echo "Ingen meldinger på engelsk (en) på enhet $DEVICE ($NAME)."
    fi
    echo "-----------------------------------------------------"
  done
}

# Funksjon for å sette enhetens hostname
function set_device_hostname {
    local device_name="$1"
    local info=($(get_device_info "$device_name"))
    local device_id="${info[1]}"  # Hent ID fra info
    timestamp=$(hent_timestamp)

    if [[ -z "$device_id" ]]; then
        echo "Ingen enhet med navnet $device_name funnet i device_info_map!"
        return 1
    fi

    # Koble til enheten via adb og sett hostname
    echo "Setter hostname til $device_name på enhet med ID: $device_id"
    adb -s "$device_id" shell "su -c 'setprop net.hostname $device_name'"  # Nettverksnavn
    adb -s "$device_id" shell "su -c 'settings put global device_name $device_name'"  # Globalt enhetsnavn (GUI)
    adb -s "$device_id" shell "su -c 'settings put secure bluetooth_name $device_name'"  # Bluetooth-enhetsnavn

    #adb -s "$device_id" shell "su -c 'cp /data/misc/bluedroid/bt_config.conf /sdcard/Documents/$timestamp-bt_config_backup.conf'"
    #adb -s "$device_id" shell "su -c 'cat /sdcard/Documents/$timestamp-bt_config_backup.conf'"
    adb -s "$device_id" shell "su -c 'sed -i \"s/^Name = .*/Name = $device_name/\" /data/misc/bluedroid/bt_config.conf'"
    #adb -s "$device_id" shell "su -c 'cat /data/misc/bluedroid/bt_config.conf'"    

    #adb -s "$device_id" shell "su -c 'service call bluetooth_manager 6 s16 $device_name'"
    #adb -s "$device_id" shell "su -c 'service call bluetooth_manager 9'"
    #adb -s "$device_id" shell "su -c 'service call bluetooth_manager 8'"

    # Verifiser endringen
    local current_nethostname=$(adb -s "$device_id" shell getprop net.hostname)
    local current_devicename=$(adb -s "$device_id" shell "su -c 'settings get global device_name'")
    local current_bthostname=$(adb -s "$device_id" shell "su -c 'settings get secure bluetooth_name'")
    local current_btdevicename=$(adb -s "$device_id" shell "su -c 'grep \"^Name =\" /data/misc/bluedroid/bt_config.conf | sed \"s/Name = //\"'")

    if [[ "$current_nethostname" == "$device_name" && "$current_devicename" == "$device_name" && "$current_bthostname" == "$device_name"  && "$current_btdevicename" == "$device_name" ]]; then
        echo "Hostname er satt til $device_name på enhet med ID: $device_id"
        return 0
    else
        echo "Feil: Hostname ble ikke endret riktig på enhet med ID: $device_id!"
        return 1
    fi
}

# Funksjon for å sjekke om enheten er online før ADB-kommandoer
function sjekk_enhets_tilkobling {
    local NAME=$1
    local DEVICE=$2

    if [[ -z "$DEVICE" ]]; then
        DEVICE=$(hent_enhets_id "$NAME")
    fi

  if ! adb -s $DEVICE get-state 1>/dev/null 2>/dev/null; then
    echo "Enheten $NAME ($DEVICE) er ikke tilgjengelig eller ikke koblet til."
    return 1  # Returner feil hvis enheten ikke er tilgjengelig
  fi

  return 0
}

# Funksjon for å sjekke om enhetens navn er spesifisert
function check_device_name {
    local device_name="$1"
    if [[ -z "$device_name" ]]; then
        echo "Du må spesifisere et enhetsnavn!"
        return 1
    fi
}

# Funksjon for å skru av ipv6 på en enhet
function skru_av_ipv6 {
    local device_id="$1"
    echo "Skru av IPv6 på enhet med ID: $device_id"

    adb -s $device_id shell "su -c 'sysctl -w net.ipv6.conf.all.disable_ipv6=1'"
    adb -s $device_id shell "su -c 'sysctl -w net.ipv6.conf.lo.disable_ipv6=1'"
    adb -s $device_id shell "su -c 'sysctl -w net.ipv6.conf.wlan0.disable_ipv6=1'"

    echo "IPv6 er skrudd av på enhet med ID: $device_id"
}

# Funksjon for å hente enhets_id basert på enhetsnavn
function hent_enhets_id {
    local enhets_navn="$1"
    local enhets_id=$(echo "${device_info_map[$enhets_navn]}" | cut -d':' -f1)

    if [[ -z "$enhets_id" ]]; then
        echo "Ingen enhet med navnet $enhets_navn funnet!"
        return 1
    fi

    # Returner device_id hvis alt er i orden
    echo "$enhets_id"
}

# Funksjon for å hente enhets_navn basert på enhets-ID
function hent_enhets_navn {
    local enhets_id="$1"
    local enhets_navn=""
    for name in ${(k)device_info_map}; do
        local info=(${(s/:/)device_info_map[$name]})
        if [[ "${info[1]}" == "$enhets_id" ]]; then
            enhets_navn="$name"
            break
        fi
    done

    if [[ -z "$enhets_navn" ]]; then
        echo "Ingen enhet med id $enhets_id funnet!"
        return 1
    fi

    # Returner device_id hvis alt er i orden
    echo "$enhets_navn"
}

# Funksjon for å hente ID, passord, passordstyrke og type fra map
function get_device_info {
    local device_name=$1
    local info="${device_info_map[$device_name]}"
    local id=$(echo "$info" | cut -d':' -f1)
    local passord=$(echo "$info" | cut -d':' -f2)
    local passordstyrke=$(echo "$info" | cut -d':' -f3)
    local type=$(echo "$info" | cut -d':' -f4)

    echo "$id" "$passord" "$passordstyrke" "$type"
}

# Funksjon for å hente portnummer fra enhetens ID
function hent_enhets_port {
    local device_name=$1
    # Hent informasjon fra device_info_map
    local info="${device_info_map[$device_name]}"
    local device_id=$(echo "$info" | cut -d':' -f1)  # Ekstraher ID fra streng

    # Returner portnummer hvis ID-en er gyldig og starter med 'emulator-'
    if [[ $device_id == emulator-* ]]; then
        port=${device_id#emulator-} # Ekstraher portnummeret fra "emulator-<port>"
        echo $port
    else
        echo "Feil - ikke emulator-enhet. Klarte ikke finne portnummeret."
        return 1
    fi
}

# Funksjon for å printe ut alle enheter med type inkludert
function print_device_map {
    for name in ${(k)device_info_map}; do
        local info=(${(s/:/)device_info_map[$name]})
        echo "Enhet: $name, ID: ${info[1]}, Passord: ${info[2]}, Passordstyrke: ${info[3]}, Type: ${info[4]}"
    done
}

# Funksjon for å laste inn enhetsinformasjon, inkludert type
function last_inn_enheter {
    local config_file="$BASE_DIR/enheter.conf"

    if [[ ! -f $config_file ]]; then
        echo "Konfigurasjonsfilen $config_file finnes ikke!"
        return 1
    fi

    local current_device=""
    while IFS='=' read -r key value; do
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)

        if [[ -z "$key" && -z "$value" ]]; then
            continue
        fi

        if [[ $key == \[*\] ]]; then
            current_device=$(echo $key | tr -d '[]')
        elif [[ $key == "id" && -n $current_device ]]; then
            id=$value
        elif [[ $key == "passord" && -n $current_device ]]; then
            passord=$value
        elif [[ $key == "passordstyrke" && -n $current_device ]]; then
            passordstyrke=$value
        elif [[ $key == "type" && -n $current_device ]]; then
            type=$value
            # Kombiner informasjonen i én streng separert med kolon
            device_info_map[$current_device]="$id:$passord:$passordstyrke:$type"
        fi
    done < "$config_file"
}

# Funksjon for å utføre en annen funksjon for alle enheter dersom "ALLE" er spesifisert
function utfør_for_alle {
    local funksjonsnavn="$1"
    local device_name="$2"

    if [[ "$device_name" == "ALLE" ]]; then
        for device_name in ${(k)device_info_map}; do
            $funksjonsnavn "$device_name"
        done
        return 0  # Utført for alle, så avslutt tidlig
    fi

    return 1  # Ikke "ALLE", fortsett i den respektive funksjonen
}

# Funksjon for å sjekke om Briar kjører
function er_briar_aktiv {
    local device_id="$1"
    local briar_pid=$(adb -s "$device_id" shell pidof org.briarproject.briar.android)
    
    if [[ -n "$briar_pid" ]]; then
        echo "$briar_pid"  # Returner PID hvis Briar kjører
    fi
    # Ingen return hvis Briar ikke kjører
}


# Funksjon for å starte Briar eller bringe den til forsiden
function start_briar {
    local device_id="$1"
    echo "Starter Briar på enhet: $device_id"

    if [[ -n $(er_briar_aktiv "$device_id") ]]; then
        if adb -s "$device_id" shell dumpsys window windows | grep -q 'topApp.*org.briarproject.briar.android'; then
            echo "Briar kjører ikke i forgrunnen. Starter Briar."
            adb -s "$device_id" shell am start -n org.briarproject.briar.android/.splash.SplashScreenActivity
        else
            echo "Briar kjører allerede i forgrunnen."
        fi
    else
        echo "Briar kjører ikke. Starter appen."
        adb -s "$device_id" shell am start -n org.briarproject.briar.android/.splash.SplashScreenActivity
    fi

}

function stopp_briar {
    local device_id="$1"
    echo "Stopper Briar på enhet: $device_id"
    
    # Bruk `am start` for å bringe Briar til forsiden
    adb -s "$device_id" shell "am force-stop org.briarproject.briar.android"
}


function hent_timestamp {
    echo $(date +"%Y-%m-%dT%H-%M-%S")
}

function lagre_tor_sockets {
    local device_id="$1"
    local enhets_navn=$(hent_enhets_navn "$device_id")
    local TIMESTAMP=$(hent_timestamp)
    local TOR_BASE_FILE_NAME="${TOR_DIR}/${TIMESTAMP}-${enhets_navn}"
    local TOR_SOCKETS_FILE_NAME="$TOR_BASE_FILE_NAME-tor-sockets.txt"

    local TOR_TRUE=$(adb -s $device_id shell su -c "ls $TOR_DIR/*-is-*or.txt > /dev/null 2>&1 && echo 'EXISTS' || echo 'NOT_EXISTS'")

    if [ "$TOR_TRUE" = "EXISTS" ]; then
        echo "Tor er aktivt på enhet $enhets_navn. Logger Tor sockets."
        adb -s $device_id shell su -c "netstat -tulpan | grep tor > $TOR_SOCKETS_FILE_NAME"
    else
        echo "Tor er ikke aktivt på $enhets_navn. Hopper over logging av Tor sockets."
    fi

}

# Funksjon for å logge ut fra Briar
function logg_ut_briar {
    local device_name="$1"

    # Sjekk om vi skal utføre for alle enheter
    utfør_for_alle "logg_ut_briar" "$device_name" && return

    # Sjekk enhetsnavn og hent device_id
    check_device_name "$device_name" || return 1
    local device_id=$(hent_enhets_id "$device_name") || return 1

    # Sjekk om Briar kjører ved å få PID
    local briar_pid=$(er_briar_aktiv "$device_id")
    
    if [[ -n "$briar_pid" ]]; then
        # Hvis Briar kjører, start eller bring den til forsiden
        start_briar "$device_id"
        sleep 2

        echo "Logger ut fra Briar på enhet: $device_name"
        
        # Logg ut fra Briar
        sleep 0.3
        tap_screen_back "$device_id"  # Hamburger meny
        #echo "DEBUG: tapper back" >&2
        sleep 0.3
        tap_screen_back "$device_id"  # Hamburger meny
        #echo "DEBUG: tapper back" >&2
        sleep 0.3
        tap_screen_prosent "$device_id" 50 45  # Sign out
        #echo "DEBUG: tapper 50% 45% for sign out knapp" >&2
        
        loggut_ventetid=5
        #echo "DEBUG: Venter i $loggut_ventetid sekunder før vi sjekker om Briar ble lukket." >&2
        sleep $loggut_ventetid

        # Sjekk om Briar fortsatt kjører etter utlogging
        briar_pid=$(er_briar_aktiv "$device_id")
        #echo "DEBUG: Briar PID etter utlogging: $briar_pid" >&2

        if [[ -n "$briar_pid" ]]; then
            echo "Briar ble ikke avsluttet for $device_name ($device_id)"
            stopp_briar "$device_id"
            echo "Prøver å tvinge stopp av Briar for $device_name"
        else
            echo "Briar ble stengt korrekt etter utlogging."
        fi
    else
        echo "Briar kjører ikke, hopper over utlogging."
    fi
}



function velg_samtale_sit_1_3 {
    local device_name="$1"

    # Sjekk enhetsnavn og hent device_id
    check_device_name "$device_name" || return 1
    local device_id=$(hent_enhets_id "$device_name") || return 1

    #adb -s "$device_id" shell "input keyevent 61"
    #sleep 0.2
    sleep 0.5
    adb -s "$device_id" shell "input tap 557 434"
    #sleep 0.2
    sleep 0.5
    adb -s "$device_id" shell "input tap 557 434"
    #adb -s "$device_id" shell "input keyevent 61"
    #sleep 0.2
    #adb -s "$device_id" shell "input keyevent 66"
    #sleep 0.2

}

function velg_samtale_sit_4 {
    local device_name="$1"

    # Sjekk enhetsnavn og hent device_id
    check_device_name "$device_name" || return 1
    local device_id=$(hent_enhets_id "$device_name") || return 1

    #adb -s "$device_id" shell "input keyevent 61"
    #sleep 0.2
    sleep 0.5
    adb -s "$device_id" shell "input tap 536 571"
    #sleep 0.2
    sleep 0.5
    adb -s "$device_id" shell "input tap 569 422"
    #adb -s "$device_id" shell "input keyevent 61"
    #sleep 0.2
    #adb -s "$device_id" shell "input keyevent 66"
    #sleep 0.2

}


function naviger_til_kanal {
    local device_id="$1"

    # Aktiver kanal
    tap_screen_back "$device_id"  # Hamburger meny
    sleep 1
    tap_screen_back "$device_id"  # Hamburger meny
    sleep 1
    adb -s "$device_id" shell "input tap 560 2220"
    sleep 1
    #for i in $(seq 1 8); do
    #    adb -s "$device_id" shell "input keyevent 61"
    #    sleep 0.3
    #done  # Naviger til Sign out

    #adb -s "$device_id" shell "input keyevent 66"  # Åpner "Connections"
    
    #sleep 2
} 


function fra_samtale_til_burger {
    device="$1"

    sleep 1
    
    echo "trykker back"
    adb -s "$device" shell "input tap 76 192"  # Back fra selve chatten
    
    sleep 1
    
    echo "trykker back"
    adb -s "$device" shell "input tap 76 192"  # Back fra selve chatten
    
    sleep 1
} 


function tilbake_til_forumet {
    device="$1"

    sleep 1
    
    echo "Trykker forum"
    adb -s "$device" shell input tap 500 710  # Velg forum    
    
    sleep 1
    
    echo "Velger forum"
    adb -s "$device" shell input tap 500 420  # Velg det aktuelle forumet
    
    sleep 1

}


function tilbake_til_blogg {
    device="$1"

    sleep 1
    
    echo "Trykker blogg"
    adb -s "$device" shell input tap 500 810  # Velg blogg    
    
    sleep 1
    
} 

    
# Funksjon for å klikk på skjermen
function tap_screen_prosent {
  local device=$1
  local X_PERCENT=$2
  local Y_PERCENT=$3
  local SCREEN_DIMENSIONS=$(adb -s $device shell wm size)
  
  # Hent skjermens bredde og høyde
  local WIDTH=$(echo "$SCREEN_DIMENSIONS" | awk '{print $3}' | cut -d'x' -f1)
  local HEIGHT=$(echo "$SCREEN_DIMENSIONS" | awk '{print $3}' | cut -d'x' -f2)
  
  # Beregn trykkpunktet basert på prosent av skjermens bredde og høyde
  local TAP_X=$((WIDTH * X_PERCENT / 100))
  local TAP_Y=$((HEIGHT * Y_PERCENT / 100))
  
  #echo "Sender point event til posisjon ($TAP_X, $TAP_Y) på enhet $device (${(k)device_map[(R)$device]}). X: $X_PERCENT%, Y: $Y_PERCENT%"
  
  # Send tap til den spesifiserte posisjonen
  adb -s $device shell input tap $TAP_X $TAP_Y
}


function tap_screen_back {
    local device_id=$1
    local x_prosent=7
    local y_prosent=8
    tap_screen_prosent "$device_id" $x_prosent $y_prosent # back
}


function toggle_kanal {
    local device_name="$1"
    local kanal="$2"
    local trykk_antall=3  # Default til Tor

    # Sjekk enhetsnavn og hent device_id
    check_device_name "$device_name" || return 1
    local device_id=$(hent_enhets_id "$device_name") || return 1

    # Sjekk om Briar kjører
    if [[ -z $(er_briar_aktiv "$device_id") ]]; then
        echo "Briar kjører ikke på enhet: $device_id" >&2
        start_briar $device_id
        #return 1
    fi

    naviger_til_kanal "$device_id"
    echo "Velger kanal: $kanal på enhet: $device_id"

    local x_prosent=51.8
    local y_prosent=0
    if [[ "$kanal" == "Tor" || "$kanal" == "tor" ]]; then
        #trykk_antall=3
        #sleep 1
        #y_koordinat=517
        y_prosent=21
        #echo "Trykker på Tor koordinater: 925 517"
        #adb -s "$device_id" shell "input tap 925 517"
    elif [[ "$kanal" == "WiFi" || "$kanal" == "wifi" ]]; then
        #trykk_antall=4
        #sleep 1
        #y_koordinat=1170
        #y_koordinat=1082
        y_prosent=45.5
        #echo "Trykker på WiFi koordinater: 940 1170"
        #adb -s "$device_id" shell "input tap 940 1170"
    elif [[ "$kanal" == "Bluetooth" || "$kanal" == "bt" ]]; then
        #trykk_antall=5
        #sleep 1
        #y_koordinat=1663
        #y_koordinat=1550
        #y_koordinat=1666
        y_prosent=69
        #echo "Trykker på Bluetooth koordinater: 900 1663"
        #adb -s "$device_id" shell "input tap 900 1663"
    fi
    sleep 1

    #echo "Trykker på koordinater: $x_koordinat $y_koordinat for kanal: $kanal"
    echo "Trykker på %-koordinater: $x_prosent $y_prosent for kanal: $kanal"
    #adb -s "$device_id" shell "input tap $x_koordinat $y_koordinat"

    tap_screen_prosent "$device_id" $x_prosent $y_prosent
    
    sleep 0.5
    #for i in $(seq 1 $trykk_antall); do
    #    adb -s "$device_id" shell "input keyevent 61"
    #    sleep 0.5
    #done
    
    #adb -s "$device_id" shell "input keyevent 66"  # Aktiverer kanal

    # Back
    #tap_screen_back "$device_id"  # Back
    tap_screen_back "$device_id"
    sleep 1

    #for i in $(seq 1 4); do

    #    adb -s "$device_id" shell "input keyevent 61"
    #    echo "61"
    #    sleep 0.2
    #done
    
    #adb -s "$device_id" shell "input keyevent 66" # gå inn
    #sleep 0.5

    #fi
}


function restart_enhet {
    local enhetsnavn="$1"
    local enhets_id=$(hent_enhets_id "$enhetsnavn")
    echo "Restarter enhet: $enhetsnavn ($enhets_id)"
    adb -s $enhets_id reboot
}


# Funksjon for å logge inn Briar
function logg_inn_briar {
    local device_name="$1"

    # Sjekk om vi skal utføre for alle enheter
    utfør_for_alle "logg_inn_briar" "$device_name" && return

    # Sjekk enhetsnavn og hent device_id og passord
    check_device_name "$device_name" || return 1
    local device_id=$(hent_enhets_id "$device_name") || return 1
    local info=($(get_device_info "$device_name"))
    local password="${info[2]}"

    # Start Briar eller bring den til forsiden
    start_briar "$device_id"
    sleep 2

    echo "Logger inn på Briar på enhet: $device_id"
    # Skriv inn passord for å logge inn
    adb -s "$device_id" shell input text "$password"
    adb -s "$device_id" shell "input keyevent 66"  # Trykk Enter
}


last_inn_enheter
#print_device_map
