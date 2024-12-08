#!/bin/zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map
source "$BASE_DIR/felles.sh"

# Funksjon for å sette enhetens hostname
function ping_hostname {
    local device_name="$1"
    local hostname="$2"
    local nPackets="$3"
    local info=($(get_device_info "$device_name"))
    local device_id="${info[1]}"  # Hent ID fra info


    if [[ -z "$device_id" ]]; then
        echo "Ingen enhet med navnet $device_name funnet i device_info_map!"
        return 1
    fi

    adb -s "$device_id" shell "su -c 'ping -c $nPackets $hostname'"
}

# Hovedskript logikk
target_device=$1
hostname=$2
nPackets=$3

if [[ -n $target_device && $target_device != "ALLE" ]]; then
    # Konfigurer kun enhet med navnet $target_device
    echo "Live on three"
    ping_hostname "$target_device" "$hostname" "$nPackets"
else
    # Hvis ingen spesifikk enhet er valgt, konfigurer alle enheter i device_info_map
    echo "Live on three"
    for device_name in ${(k)device_info_map}; do
        ping_hostname "$device_name" "$hostname" "$nPackets"
    done
fi


