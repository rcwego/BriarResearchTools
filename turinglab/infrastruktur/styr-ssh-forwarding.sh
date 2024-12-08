#!/bin/zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map og relevante funksjoner
source "$BASE_DIR/felles.sh"

# SSH-porter for begge hostene (felles port 5037? frida port 27042?)
FORWARD_HOST_1=(-L 9999:localhost:9999)
FORWARD_HOST_2=(-L 9999:localhost:9999)

# Host IP-er
HOST_1=$EKSTERN_1
HOST_2=$EKSTERN_2

# Sjekk at brukeren har gitt et argument (start eller stopp)
if [[ -z "$1" ]]; then
    echo "Du må spesifisere enten 'start' eller 'stopp' som parameter."
    exit 1
fi

# Funksjon for å legge til porter fra device_info_map basert på type
function legg_til_device_porter {
    for device_name in ${(k)device_info_map}; do
        local info=($(get_device_info "$device_name"))  # Henter id, passord, passordstyrke og type
        local device_id=${info[1]}
        local device_type=${info[4]}

        # Hvis enheten er knyttet til ekstern-1, legg til port i FORWARD_HOST_1
        if [[ $device_type == "ekstern-1" ]]; then
            local port=$(hent_enhets_port "$device_name")
            if [[ -n $port ]]; then
                # Legg til både hovedporten og hovedport + 1
                FORWARD_HOST_1+=("-L ${port}:localhost:${port}")
                local additional_port=$((port + 1))
                FORWARD_HOST_1+=("-L ${additional_port}:localhost:${additional_port}")
            fi

        # Hvis enheten er knyttet til ekstern-2, legg til port i FORWARD_HOST_2
        elif [[ $device_type == "ekstern-2" ]]; then
            local port=$(hent_enhets_port "$device_name")
            if [[ -n $port ]]; then
                # Legg til både hovedporten og hovedport + 1
                FORWARD_HOST_2+=("-L ${port}:localhost:${port}")
                local additional_port=$((port + 1))
                FORWARD_HOST_2+=("-L ${additional_port}:localhost:${additional_port}")
            fi
        fi
    done
}

# Funksjon for å starte SSH-tilkoblinger
function start_forwarding {
    # Legg til porter fra device_info_map dynamisk basert på type
    legg_til_device_porter

    # Start SSH-tilkoblinger
    echo "Starter SSH-tilkobling til host 1 ($HOST_1) med forwarding av porter:"
    echo "${FORWARD_HOST_1[@]}"
    ssh -4N "${FORWARD_HOST_1[@]}" master@$HOST_1 &

    echo "Starter SSH-tilkobling til host 2 ($HOST_2) med forwarding av porter:"
    echo "${FORWARD_HOST_2[@]}"
    ssh -4N "${FORWARD_HOST_2[@]}" master@$HOST_2 &
}

# Funksjon for å stoppe SSH-tilkoblinger
function stop_forwarding {
    echo "Stopper alle aktive SSH-forbindelser som treffer 'grep ssh'..."
    pkill -f ssh
    echo "SSH-forbindelser stoppet."
}

# Avhengig av argumentet, start eller stopp forwarding
if [[ "$1" == "start" ]]; then
    start_forwarding
elif [[ "$1" == "stopp" ]]; then
    stop_forwarding
else
    echo "Ugyldig parameter: $1. Bruk 'start' eller 'stopp'."
    exit 1
fi
