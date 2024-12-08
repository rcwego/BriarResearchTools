#!/usr/bin/env zsh

# Finn absolutt sti til denne filen
BASE_DIR=$(dirname "$(realpath "$0")")

# For å bruke device_info_map
source "$BASE_DIR/../../ressurser/felles.sh"

ENHETSNAVN=$1
LOKAL_STI=${3:-"./kopier"} # Sett destinasjonssti: Hvis argument 3 er gitt, bruk den, ellers bruk './kopier'
SITUASJON=${2:+situasjon_$2-} # Situasjonsnummer (valgfritt), hvis angitt settes som 'situasjon_$2-'

# Funksjon for å hente pakkedumpfiler fra WiFi- og Bluetooth-katalogene på enhetene
function hent_lagringsområde {
  local ENHETSNAVN=$1
  local ENHETSID=$(hent_enhets_id "$ENHETSNAVN") || return 1
  local timestamp=$(hent_timestamp)
  local destinasjon=$LOKAL_STI/$ENHETSNAVN/$SITUASJON$timestamp

  echo $destinasjon

  if [ ! -d "$destinasjon" ]; then
    mkdir -p "$destinasjon"
    chmod -R 755 "$destinasjon"
  fi

  # Sjekk om både ENHETSID og LOKALLAGRING_DIR ikke er tomme
  if [ -n "$ENHETSID" ] && [ -n "$LOKALLAGRING_DIR" ]; then

    # Sjekk om mappen eksisterer, og hvis den eksisterer, tøm den
    adb -s $ENHETSID shell "su -c 'if [ -d $LOKALLAGRING_DIR ]; then rm -rf $LOKALLAGRING_DIR/*; else mkdir -p $LOKALLAGRING_DIR; fi'"
    
    # Kopier Briar-data til en midlertidig mappe på enheten
    adb -s $ENHETSID shell "su -c 'cp -r $BRIAR_LAGRINGSSTI $LOKALLAGRING_DIR'"

    # Henter Briar-data
    adb -s $ENHETSID pull "$LOKALLAGRING_DIR/." "$destinasjon/" 2>&1
    
    if [ $? -eq 0 ]; then
      echo "Henting av lagringsområde fullført: $destinasjon"
    
      zip -r "$destinasjon.zip" "$destinasjon" -x "*.DS_Store"
    
      if [ $? -eq 0 ]; then
        echo "Zipping fullført: $destinasjon.zip"
      else
        echo "Feil under zipping" >&2
      fi
    
    else
      echo "Feil under henting av lagringsområde" >&2
    fi

  
  else
    echo "EnhetsID er null eller tom. Kan ikke hente lagringsområde." >&2

  fi

}

# Hovedlogikk for å håndtere en spesifikk enhet eller alle enheter
hent_lagringsområde "$ENHETSNAVN"

echo "Ferdig med å hente lagringsområde for enhet: $ENHETSNAVN"