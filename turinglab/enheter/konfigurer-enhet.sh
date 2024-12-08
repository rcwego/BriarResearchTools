#!/bin/zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

source "$BASE_DIR/felles.sh"

# Funksjon for å hente brukernavn og passord for en gitt enhet
function konfigurer_avd {
    enhets_navn=$1
    enhets_id=$(hent_enhets_id "$1")
    
    set_device_hostname "$enhets_navn"
    skru_av_ipv6 "$enhets_id"
}

# Hovedskript logikk
target_device=$1

if [[ -n $target_device && $target_device != "ALLE" ]]; then
    # Konfigurer kun enhet med navnet $target_device
    echo "Konfigurerer kun enhet: $target_device"
    konfigurer_avd "$target_device"
else
    # Hvis ingen spesifikk enhet er valgt, konfigurer alle enheter i device_info_map
    echo "Konfigurerer alle enheter..."
    for device_name in ${(k)device_info_map}; do
        konfigurer_avd "$device_name"
    done
fi
