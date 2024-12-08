#!/bin/zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map og relevante funksjoner
source "$BASE_DIR/felles.sh"

# Funksjon for å hente brukernavn og passord for en gitt enhet
function konfigurer_briar {
    local device_name=$1
    local info=($(get_device_info "$device_name"))  # Henter id, passord, passordstyrke og type
    local device_id="${info[1]}"  # Hent ID
    local passord="${info[2]}"  # Hent passord

    if [[ -z $device_id || -z $passord ]]; then
        echo "Ingen gyldig ID eller passord funnet for enheten: $device_name"
        return 1
    fi

    echo "Konfigurerer Briar for enhet: $device_name (ID: $device_id)"

    start_briar $device_id
    sleep 5

    # Skriv inn brukernavnet (navn på devicen)
    adb -s $device_id shell input text "$device_name"
    adb -s $device_id shell input keyevent 66
    sleep 5

    # Skriv inn passordet
    adb -s $device_id shell input text "$passord"
    sleep 5
    
    # Trykk TAB to ganger
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 61
    sleep 5

    # Skriv inn passordet igjen
    adb -s $device_id shell input text "$passord"
    sleep 5

    # Trykk ENTER
    adb -s $device_id shell input keyevent 66
    sleep 5

    # ALLOW NOTIFICATIONS
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 66
    sleep 5

    # ALLOW CONNECTIONS
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 66
    sleep 5

    # ALLOW - LET APP RUN IN BACKGROUND
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 66
    sleep 5

    # CREATE ACCOUNT
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 61
    sleep 5
    adb -s $device_id shell input keyevent 66
    sleep 5

    echo "Briar er konfigurert for enhet: $device_name"
}

# Hovedskript logikk
target_device=$1

if [[ -n $target_device && $target_device != "ALLE" ]]; then
    # Konfigurer kun enhet med navnet $target_device
    echo "Konfigurerer kun enhet: $target_device"
    konfigurer_briar "$target_device"
else
    # Hvis ingen spesifikk enhet er valgt, konfigurer alle enheter parallelt
    echo "Konfigurerer alle enheter parallelt..."
    for device_name in ${(k)device_info_map}; do
        konfigurer_briar "$device_name" &
    done
    wait  # Vent på at alle bakgrunnsprosessene er ferdige
fi
