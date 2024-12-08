import json
import os
import logging
import configparser
import argparse
import subprocess
from datetime import datetime
from datetime import timedelta
import time
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ressurser')))
from custom_formatter import CustomFormatter, RESET, YELLOW, RED, BOLD_GREEN, BOLD_RED

# Funksjon for å sette opp logger
def setup_logger(verbose_level):
    log_dir = './log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    script_navn = os.path.splitext(os.path.basename(__file__))[0]  # Hent navnet på scriptet uten filendelsen
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    log_filnavn = f'{script_navn}-{timestamp}.log'
    log_file = os.path.join(log_dir, log_filnavn)


    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Alltid logg DEBUG til filen

    # Filhandler (Logger alle nivåer til fil)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

    # Konsollhandler (Logger avhengig av verbose nivå)
    console_handler = logging.StreamHandler()

    if verbose_level == 2:
        console_handler.setLevel(logging.DEBUG)  # Logg DEBUG til konsollen hvis vv
    elif verbose_level == 1:
        console_handler.setLevel(logging.INFO)  # Logg INFO til konsollen hvis v
    else:
        console_handler.setLevel(logging.WARNING)  # Logg WARNING som standard
    
    #console_format = logging.Formatter('%(levelname)s - %(message)s')
    #console_handler.setFormatter(console_format)
    console_handler.setFormatter(CustomFormatter())


    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_device_arkitektur(type, id):
    logging.debug(f"Enhetstype: {type}, ID: {id}")
    telefontype = "Google Pixel 7a"
    enhetstype = "ukjent enhetstype"
    prosessor = "ukjent prosessor"
    minne = "ukjent minne"
    arkitektur = "ukjent arkitektur"
    
    if type in ["ekstern-1", "ekstern-2"]:
        enhetstype = "emulator"
        arkitektur = "x64"
    
        if type in ["ekstern-1"]:
            prosessor = "Intel Core i7-1260p"
            minne = "32 GB LPDDR5"
    
        elif type in ["ekstern-2"]:
            prosessor = "Intel Core i9-9900K"
            minne = "48 GB DDR4"

    elif type in ["lokal"]:
        enhetstype = "emulator"
        arkitektur = "arm64"
        prosessor = "Apple M2"
        minne = "24 GB LPDDR5"
    
    elif type in ["fysisk"]:
        enhetstype = "fysisk"
        arkitektur = "arm64"
        prosessor = "Google Tensor G2"
        minne = "8 GB LPDDR5"

        if id == "34061FDH2003BL":
            telefontype = "Google Pixel 7"

    return enhetstype, arkitektur, telefontype, prosessor, minne


def beregn_tid_per_passord(enhet_data):
    """
    Beregn tid per passord basert på total tid og totalt antall forsøk.

    Args:
        enhet_data (dict): En ordbok som inneholder informasjon om enheten, inkludert:
            - 'total_tid' (float): Total tid brukt på å verifisere passord.
            - 'gjettet_passordnummer' (int): Totalt antall forsøk på å verifisere passord.
            - 'enhet_id' (str): Enhetens ID (valgfritt).

    Returns:
        None: Funksjonen oppdaterer 'enhet_data' ordboken med en ny nøkkel 'tid_per_passord' som representerer
        gjennomsnittlig tid brukt per passord i sekunder, avrundet til to desimaler.

    Logger:
        Informasjonsmelding som viser tid per passord for enheten.
    """
    total_tid = enhet_data.get('tid_brukt', '0')
    try:
        # Splitter opp timeverdiene
        hours, minutes, seconds = map(int, total_tid.split(':'))
        
        # Konverterer til dager og timer ved å bruke timedelta
        time_delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        
        logging.debug(f"Total tid: {time_delta}")
    except ValueError:
        logging.warning("Ugyldig tid-format:", total_tid)
        time_delta = timedelta()  # Setter time_delta til 0 om formatet er ugyldig

    # Logger total tid i sekunder
    total_tid_i_sekunder = time_delta.total_seconds()
    logging.debug(f"Total tid for enhet {enhet_data.get('enhet')}: {total_tid_i_sekunder} sekunder")

    # Henter totalt antall forsøk og unngår divisjon med null
    gjettet_passordnummer = enhet_data.get('gjettet_passordnummer', 1)  # Setter til 1 som default for å unngå divisjon med null
    logging.debug(f"Totalt antall forsøk for enhet {enhet_data.get('enhet')}: {gjettet_passordnummer}")

    # Beregner tid per passord i sekunder
    tid_per_passord = total_tid_i_sekunder / gjettet_passordnummer
    enhet_data['tid_per_passord'] = round(tid_per_passord, 2)  # Legg til tid per passord med 2 desimaler

    # Logger tid per passord
    logging.info(f"Tid per passord for enhet {enhet_data.get('enhet')}: {enhet_data['tid_per_passord']} sekunder")


def start_briar(enhet_navn, enhet_id):
    """
    Starter Briar-applikasjonen på enheten ved hjelp av adb.

    Args:
        enhet_navn (str): Navnet på enheten.
        enhet_id (str): ID-en til enheten.

    Returns:
        bool: True hvis Briar ble startet vellykket, ellers False.
    """
    pakke_navn = "org.briarproject.briar.android"
    aktivitet_navn = ".splash.SplashScreenActivity"
    
    try:
        resultat = subprocess.run(
            ["adb", "-s", enhet_id, "shell", "am", "start", "-n", f"{pakke_navn}/{aktivitet_navn}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if resultat.returncode != 0:
            logging.error(f"Feil ved oppstart av Briar på enhet {enhet_navn} (ID: {enhet_id}): {resultat.stderr.decode('utf-8')}")
            return False
        else:
            logging.info(f"Briar startet på enhet {enhet_navn} (ID: {enhet_id})")
            return True
    except Exception as e:
        logging.error(f"En feil oppstod ved oppstart av Briar på enhet {enhet_navn} (ID: {enhet_id}): {e}")
        return False

def finn_nyeste_json_fil(resultat_mappe='./resultater'):
    """
    Finner den nyeste JSON-filen i resultatkatalogen.

    Args:
        resultat_mappe (str): Katalogen der resultatfilene ligger.

    Returns:
        str: Stien til den nyeste JSON-filen.

    Raises:
        FileNotFoundError: Hvis ingen JSON-filer finnes i katalogen.
    """
    json_filer = [f for f in os.listdir(resultat_mappe) if f.endswith('datasett.json')]
    if not json_filer:
        raise FileNotFoundError(f"Ingen JSON-filer funnet i {resultat_mappe}.")
    
    nyeste_fil = max(json_filer, key=lambda f: os.path.getmtime(os.path.join(resultat_mappe, f)))
    return os.path.join(resultat_mappe, nyeste_fil)

def les_config(config_fil='./../ressurser/enheter.conf'):
    """
    Leser konfigurasjonsfilen for enheter.

    Args:
        config_fil (str): Stien til konfigurasjonsfilen.

    Returns:
        configparser.ConfigParser: Konfigurasjonsobjektet.
    """
    config = configparser.ConfigParser()
    config.read(config_fil)
    return config

def verifiser_passord(enhet_id, passord):
    """
    Verifiserer passordet ved å skrive det inn på enheten ved hjelp av adb.

    Args:
        enhet_id (str): ID-en til enheten.
        passord (str): Passordet som skal verifiseres.

    Returns:
        bool: True hvis passordet ble verifisert vellykket, ellers False.
    """
    try:
        resultat = subprocess.run(
            ["adb", "-s", enhet_id, "shell", "input", "text", passord],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if resultat.returncode != 0:
            logging.error(f"Feil ved verifisering av passord på enhet {enhet_id}: {resultat.stderr.decode('utf-8')}")
            return False
        return True
    except Exception as e:
        logging.error(f"En feil oppstod ved verifisering av passord på enhet {enhet_id}: {e}")
        return False

def skriv_inn_passord_og_trykk_enter(enhet_id, passord):
    """
    Skriver inn passordet og trykker enter på enheten ved hjelp av adb.

    Args:
        enhet_id (str): ID-en til enheten.
        passord (str): Passordet som skal skrives inn.
    """
    try:
        # Skriv inn passord
        subprocess.run(
            ["adb", "-s", enhet_id, "shell", "input", "text", passord],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Trykk enter
        subprocess.run(
            ["adb", "-s", enhet_id, "shell", "input", "keyevent", "66"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logging.info(f"Passord skrevet inn og enter trykket på enhet {enhet_id}")
    except Exception as e:
        logging.error(f"En feil oppstod ved innskriving av passord på enhet {enhet_id}: {e}")

def lagre_oppdatert_datasett(data, original_fil):
    """
    Lagrer det oppdaterte datasettet til en ny fil med suffikset '_verifisert.json'.

    Args:
        data (list): Det oppdaterte datasettet.
        original_fil (str): Stien til den originale JSON-filen.
    """
    ny_fil = original_fil.replace('.json', '_verifisert.json')
    with open(ny_fil, 'w') as f:
        json.dump(data, f, indent=4)
    logging.info(f"Oppdatert datasett lagret til {ny_fil}")

def main(resultat_mappe='./resultater', config_fil='./../ressurser/enheter.conf'):
    """
    Hovedfunksjon for å verifisere passord og starte Briar-applikasjonen på enheter.

    Args:
        resultat_mappe (str): Katalogen der resultatfilene ligger.
        config_fil (str): Stien til konfigurasjonsfilen for enheter.
    """

    logging.info("Starter verifisering av passord...")
    
    try:
        nyeste_fil = finn_nyeste_json_fil(resultat_mappe)
        logging.info(f"Fant nyeste JSON-fil: {nyeste_fil}")
    except FileNotFoundError as e:
        logging.error(e)
        return
    
    with open(nyeste_fil, 'r') as f:
        data = json.load(f)
    
    config = les_config(config_fil)
    
    for enhet_data in data:
        enhet_navn = enhet_data['enhet']
        status = enhet_data.get('status')

        if status not in ['suksess', 'feilet']:
            logging.info(f"Status for enhet {enhet_navn} er ikke relevant for testing: {status}")
            continue
        
        enhet_id = config[enhet_navn]['id']
        passord = config[enhet_navn]['passord']
        type = config[enhet_navn]['type']
        gjettet_passord = enhet_data.get('gjettet_passord', '')

        enhet_data['verifisert'] = False
        enhet_data['validert'] = False
        enhet_data['faktisk_passord'] = passord

        logging.info(f"Faktisk passord for enhet {enhet_navn} (ID: {enhet_id}): {passord}")

        beregn_tid_per_passord(enhet_data)
        enhetstype, arkitektur, telefontype, prosessor, minne = get_device_arkitektur(type, enhet_id)
        enhet_data['enhetstype'] = enhetstype
        enhet_data['arkitektur'] = arkitektur
        enhet_data['telefontype'] = telefontype
        enhet_data['prosessor'] = prosessor
        enhet_data['minne'] = minne

        if gjettet_passord == passord:
            enhet_data['verifisert'] = True

            logging.info(f"Passord verifisert for enhet {enhet_navn} (ID: {enhet_id})")
            

            if start_briar(enhet_navn, enhet_id):
                time.sleep(0.1)  # Vent n sekunder
                skriv_inn_passord_og_trykk_enter(enhet_id, gjettet_passord)
                
                # Spør brukeren om innloggingen var suksessfull
                while True:
                    svar = input(f"Var innloggingen suksessfull for enhet {enhet_navn} (ID: {enhet_id})? (j/n): ").strip().lower()
                    if svar in ['j']:
                        enhet_data['validert'] = True
                        break
                    elif svar in ['n']:
                        enhet_data['validert'] = False
                        break
                    else:
                        logging.error("Ugyldig svar. Vennligst svar med 'j' eller 'n'.")
        else:
            logging.warning(f"Kunne ikke verifisere passord for enhet {enhet_navn} (ID: {enhet_id}) pga. at gjettet passord er feil.")

    lagre_oppdatert_datasett(data, nyeste_fil)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verifiser passord og start Briar-applikasjonen på enheter.")
    parser.add_argument('--resultat_mappe', type=str, default='./resultater', help='Katalog for resultatfiler')
    parser.add_argument('--config_fil', type=str, default='./../ressurser/enheter.conf', help='Konfigurasjonsfil for enheter')
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Øk verbose nivå: -v for INFO, -vv for DEBUG")
    args = parser.parse_args()
    
    logger = setup_logger(args.verbose)

    main(args.resultat_mappe, args.config_fil)
