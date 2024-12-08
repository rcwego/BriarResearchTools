#!/bin/zsh

# Definer Android SDK path
ANDROID_SDK_PATH=~/Library/Android/sdk/emulator

# Definer Android AVD Home path for Windows
WINDOWS_ANDROID_AVD_HOME="C:\\Users\\master\\Desktop\\"

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map og relevante funksjoner
source "$BASE_DIR/felles.sh"

# Funksjon for å generere en start_emulatorer.bat-fil for ekstern bruk
function generer_bat_script {
    local ekstern_host=$1  # ekstern-1 eller ekstern-2
    local filnavn="start-emulatorer-$ekstern_host.bat"
    local bat_file_content=""

    # Bygg .bat-filen dynamisk basert på target_device
    for device_name in ${(k)device_info_map}; do
        local info=($(get_device_info "$device_name"))
        local port=$(hent_enhets_port "$device_name")
        local device_type="${info[4]}"

        # Hvis enheten er tilknyttet riktig ekstern vert
        if [[ "$device_type" == "$ekstern_host" ]]; then
            bat_file_content+="start /min emulator -avd $device_name -port $port\n" # Read only flagg: -read-only
        fi
    done

    # Skriv innholdet til .bat-filen
    echo -e "$bat_file_content" > $filnavn
    echo "Genererte $filnavn for $ekstern_host."
}

# Funksjon for å sende .bat-filen til Windows
function send_bat_fil_til_remote {
    local ekstern_host=$1
    local ekstern_ip=$2
    local bat_file="start-emulatorer-$ekstern_host.bat"  # Bruk unikt filnavn per host

    # Generer .bat-fil basert på den eksterne verten
    generer_bat_script "$ekstern_host"

    # Send .bat-filen til Windows
    scp $bat_file master@$ekstern_ip:"$WINDOWS_ANDROID_AVD_HOME\\"

    echo "$bat_file er sendt til $ekstern_host ($ekstern_ip). Filen må kjøres manuelt."
}

# Funksjon for å generere en .bat-fil for spesifikk enhet
function generer_bat_for_enhet {
    local avd_name=$1
    local host=$2  # ekstern-1 eller ekstern-2
    local filnavn="start-emulatorer-$host.bat"  # Bruk unikt filnavn per host
    local port=$(hent_enhets_port "$avd_name")

    echo "start /min emulator -avd $avd_name -port $port" > $filnavn # Read only flagg: -read-only
    echo "Genererte kommando for enhet: $avd_name til $filnavn."
}

# Funksjon for å generere en stopp-alle_emulatorer.bat-fil for ekstern bruk
function generer_stopp_bat_script {
    local filnavn="stopp-alle_emulatorer.bat"
    local bat_file_content=""

    # Bygg .bat-filen for å stoppe alle emulatorprosesser
    bat_file_content+="taskkill /IM qemu-system-x86_64.exe /F\n"

    # Skriv innholdet til .bat-filen
    echo -e "$bat_file_content" > $filnavn
    echo "Genererte $filnavn for å stoppe alle emulatorer."
}

# Funksjon for å sende stopp-alle_emulatorer.bat til begge maskiner
function send_stopp_bat_til_remote {
    local ekstern_ip=$1
    local bat_file="stopp-alle_emulatorer.bat"

    # Generer stopp-alle_emulatorer.bat
    generer_stopp_bat_script

    # Send .bat-filen til Windows-maskin
    scp $bat_file master@$ekstern_ip:"$WINDOWS_ANDROID_AVD_HOME\\"

    echo "$bat_file er sendt til $ekstern_ip. Filen må kjøres manuelt for å stoppe alle emulatorer."
}

function send_stopp_bat_alle {
    send_stopp_bat_til_remote "$EKSTERN_1"
    send_stopp_bat_til_remote "$EKSTERN_2"
}

# Funksjon for å starte en AVD basert på type (lokal, ekstern-1, ekstern-2)
function start_avd {
    local avd_name=$1
    local avd_full_name=$2

    # Hent portnummeret og typen fra enhetskartet
    local port=$(hent_enhets_port "$avd_name")
    local info=($(get_device_info "$avd_name"))
    local device_type="${info[4]}"

    if [[ $? -ne 0 || -z $port ]]; then
        echo "Hopper over AVD: $avd_name, da det ikke finnes et gyldig portnummer i enheter.conf"
        return 1
    fi

    # Hvis enheten er av typen "lokal"
    if [[ "$device_type" == "lokal" ]]; then
        echo "Starter lokal AVD: $avd_full_name på port: $port"
        $ANDROID_SDK_PATH/emulator -avd $avd_full_name -port $port &

    # Hvis enheten er av typen "ekstern-1"
    elif [[ "$device_type" == "ekstern-1" ]]; then
        echo "Genererer .bat-fil for ekstern-1"
        generer_bat_for_enhet "$avd_name" "ekstern-1"
        scp "start-emulatorer-ekstern-1.bat" master@$EKSTERN_1:"$WINDOWS_ANDROID_AVD_HOME\\"
        echo "start-emulatorer-ekstern-1.bat er sendt til ekstern-1. Filen må kjøres manuelt."

    # Hvis enheten er av typen "ekstern-2"
    elif [[ "$device_type" == "ekstern-2" ]]; then
        echo "Genererer .bat-fil for ekstern-2"
        generer_bat_for_enhet "$avd_name" "ekstern-2"
        scp "start-emulatorer-ekstern-2.bat" master@$EKSTERN_2:"$WINDOWS_ANDROID_AVD_HOME\\"
        echo "start-emulatorer-ekstern-2.bat er sendt til ekstern-2. Filen må kjøres manuelt."
    
    else
        echo "Ukjent type for enhet: $avd_name. Skipping..."
    fi
}

# Funksjon for å sende .bat-fil og starte den manuelt på eksterne maskiner
function send_bat_og_start_alle {
    local host=$1
    local ip=$2

    send_bat_fil_til_remote "$host" "$ip"
    echo "start-emulatorer-$host.bat er sendt til $host. Filen må kjøres manuelt."
}

# Funksjon for å stoppe en emulator basert på AVD-navnet
function stopp_avd {
    local avd_name=$1

    # Hent enhetens ID fra device_info_map
    local device_id=$(hent_enhets_id "$avd_name")
    
    if [[ $? -ne 0 || -z $device_id ]]; then
        echo "Kan ikke stoppe $avd_name: Enhets-ID ikke funnet."
        return 1
    fi

    echo "Stopper AVD: $avd_name ($device_id)"
    adb -s $device_id emu kill
}

# Funksjon for å stoppe alle kjørende emulatorer
function stopp_all_avds {
    echo "Stopper alle emulatorer..."
    for device_id in $(adb devices | grep emulator | cut -f1); do
        echo "Stopper emulator med enhets-ID: $device_id..."
        adb -s $device_id emu kill
    done
}

# Hovedskript logikk
action=$1
target_device=$2

# Sjekk om handling er start eller stopp
if [[ $action == "start" ]]; then

    # Slett gamle start_emulatorer.bat før du starter på nytt
    rm -f start-emulatorer-*.bat

    if [[ -n $target_device && $target_device != "ALLE" ]]; then
        # Hvis et spesifikt navn er gitt, start kun den enheten
        echo "Starter kun enhet: $target_device"
        start_avd "$target_device" "$target_device"
    else
        # Start alle enheter i enhetskartet
        for device_name in ${(k)device_info_map}; do
            avd_name=$(echo $device_name | cut -d'_' -f1)
            start_avd "$avd_name" "$device_name"
        done

        # Send til eksterne maskiner etter at alle enhetene er lagt til
        send_bat_og_start_alle "ekstern-1" "$EKSTERN_1"
        send_bat_og_start_alle "ekstern-2" "$EKSTERN_2"

        send_stopp_bat_alle
    fi

elif [[ $action == "stopp" ]]; then
    if [[ -n $target_device && $target_device != "ALLE" ]]; then
        # Hvis et spesifikt navn er gitt, stopp kun den enheten
        echo "Stopper kun enhet: $target_device"
        stopp_avd "$target_device"
    else
        # Stopp alle AVD-er
        stopp_all_avds
    fi
else
    echo "Ugyldig handling. Bruk 'start' eller 'stopp' som første parameter."
    exit 1
fi
