#!/usr/bin/env python3

import csv
import json
import shutil
import argparse
import logging
import os
import subprocess
import glob
from datetime import datetime
import time
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ressurser')))
from custom_formatter import CustomFormatter, RESET, YELLOW, RED, BOLD_GREEN, BOLD_RED

script_dir = os.path.dirname(os.path.realpath(__file__))
felles_path = os.path.join(script_dir, "../ressurser/felles.sh")


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


# Funksjon for å lese datasett og returnere en dict med avsendere og kanaler for en gitt situasjon
def les_datasett(datasett_sti, situasjons_nummer):
    data = {"avsendere": []}
    logger = logging.getLogger()

    try:
        with open(datasett_sti, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                if row['Situasjon'] == situasjons_nummer:
                    avsender = row['Avsender']
                    kanaler = row['Kanal'].strip().split(',')  # Splitter kanaler på komma
                    sender = next((d for d in data["avsendere"] if d["navn"] == avsender), None)
                    if sender:
                        # Legger til kanaler hvis de ikke allerede finnes
                        for kanal in kanaler:
                            if kanal not in sender['kanaler']:
                                sender['kanaler'].append(kanal.strip())
                    else:
                        # Sørger for at kanaler alltid er en liste
                        data["avsendere"].append({"navn": avsender, "kanaler": [kanal.strip() for kanal in kanaler]})
        logger.info(f"Avsendere og kanaler for situasjon {situasjons_nummer}: {data}")
        logger.info(f"Ferdig med å lese datasett {datasett_sti} for situasjonsnummer {situasjons_nummer}.")
    except Exception as e:
        logger.error(f"Feil ved lesing av datasett {datasett_sti}: {str(e)}")

    return data


# Funksjon for å kjøre zsh-skript i bakgrunnen med korrekt håndtering av stdout og stderr
def run_zsh_command_background(command):
    logging.info(f"Kjører kommando i bakgrunnen: {command}")
    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.Popen(command, shell=True, executable="/bin/zsh", stdout=devnull, stderr=devnull)
    
    except Exception as e:
    
        logging.error(f"Feil ved kjøring av kommando i bakgrunnen: {command}\nFeil: {str(e)}")
    

def run_zsh_command(command):
    logging.info(f"Kommando som skal kjøres: {command}")
    
    try:
        full_command = f"source {felles_path} && {command}"
        process = subprocess.Popen(full_command, shell=True, executable="/bin/zsh", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

        # Samle all stdout og stderr
        stdout_lines = []
        stderr_lines = []

        # Les stdout og stderr linje for linje i sanntid
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()

            if stdout_line:
                #sys.stdout.write(stdout_line)  # Skriv til terminalen umiddelbart
                #sys.stdout.flush()  # Sørg for at det blir skrevet ut med en gang
                logging.info(stdout_line.strip())
                stdout_lines.append(stdout_line.strip())  # Samle linjene
            if stderr_line:
                #sys.stdout.write(stderr_line)  # Skriv til terminalen umiddelbart
                #sys.stdout.flush()  # Sørg for at det blir skrevet ut med en gang
                logging.error(stderr_line.strip())
                stderr_lines.append(stderr_line.strip())  # Samle linjene

            if not stdout_line and not stderr_line and process.poll() is not None:
                break

        returncode = process.returncode

        # Etterligne 'subprocess.run()' sin struktur for returverdi
        result = subprocess.CompletedProcess(
            args=full_command,
            returncode=returncode,
            stdout="\n".join(stdout_lines),  # Samlet stdout
            stderr="\n".join(stderr_lines)   # Samlet stderr
        )

        if returncode == 0:
            logging.info(f"Kommando fullført: {command}")
        else:
            logging.error(f"Feil ved kjøring av kommando: {command}, returnkode: {returncode}")

        return result

    except Exception as e:
        logging.error(f"Unntak ved kjøring av kommando: {command}\nFeil: {str(e)}")
        return None



def finn_enhets_id(avsender):
    # Sjekk om avsender er en dictionary og har 'navn' som nøkkel
    if isinstance(avsender, dict) and 'navn' in avsender:
        avsender_navn = avsender['navn']  # Tving til en streng
    else:
        logging.error(f"Avsender har en uventet struktur eller mangler 'navn': {avsender}")
        return None  # Retur tidlig ved feil

    # Kjør kommando for å hente enhets-ID
    get_device_id_kommando = f"hent_enhets_id {avsender_navn}"
    result = run_zsh_command(get_device_id_kommando)

    # Sjekk om result er None før vi går videre
    if result is None:
        logging.error(f"Kommando mislyktes: {get_device_id_kommando}. Ingen resultat returnert.")
        return None
    
    # Sjekk om stdout finnes og inneholder data
    if not hasattr(result, 'stdout') or not result.stdout:
        logging.error(f"Feil: Ingen stdout returnert fra kommandoen for {avsender_navn}")
        return None
    
    enhets_id = result.stdout.strip()
    
    if not enhets_id:
        logging.error(f"Feil: Ingen enhets-ID funnet for {avsender}. Mulig feil i kommando.")
        return None
    
    logging.info(f"Funnet enhets-ID for {avsender_navn}: {enhets_id}")
    return enhets_id



def hent_pakkedumper_alle(avsendere):
    pakkedump_dest = os.path.join(script_dir, "Pakkedump/alle_pakkedumper")
    hent_pakkedump_path = os.path.join(script_dir, "Pakkedump/hent-pakkedumper.sh")
    kommando = f"{hent_pakkedump_path} {pakkedump_dest} ALLE" # Henter alle pakkedumper
    logging.info(f"Henter pakkedump for ALLE")
    run_zsh_command(kommando)


def slett_pakkedumper(avsendere):
    for avsender in avsendere:
        slett_pakkedumper_path = os.path.join(script_dir, "Pakkedump/slett-pakkedumper.sh")
        kommando = f"{slett_pakkedumper_path} enhet {avsender['navn']} ALLE" # Alle kanaler per avsender
        logging.info(f"Kjører slett-pakkedumper for avsender: {avsender['navn']}")
        run_zsh_command(kommando)


def lukk_briar(avsendere):

    for avsender in avsendere:
        enhets_id = finn_enhets_id(avsender)

        logging.debug(f"Avsender: {avsender['navn']} ({enhets_id})")

        # Kjør kommandoen for å sjekke om Briar er aktiv og få PID
        er_briar_aktiv = f"er_briar_aktiv {enhets_id}"
        logging.debug(f"Kommando: {er_briar_aktiv}")
        result = run_zsh_command(er_briar_aktiv)
        
        # Håndter resultatet basert på om det returneres en PID
        if result and result.stdout.strip():  # Hvis PID returneres
            briar_pid = result.stdout.strip()
            logging.warning(f"Briar kjører på enhet {avsender['navn']} (PID: {briar_pid}), lukker Briar...")
            logg_ut_briar = f"logg_ut_briar {avsender['navn']}"
            run_zsh_command(logg_ut_briar)

        else:  # Hvis ingen PID returneres, antar vi at Briar ikke kjører
            logging.info(f"Briar er ikke aktiv på enhet {avsender['navn']}, ingen handling nødvendig.")


def start_pakkedumper(avsendere):
    for avsender in avsendere:
        kanaler = avsender["kanaler"]
        logging.info(f"Avsender {avsender['navn']} sine kanaler: {kanaler}")

        # Håndter kanalene separat
        for kanal in kanaler:
            logging.info(f"Avsender {avsender['navn']} har {kanal} som kanal")
            styr_opptak_path = os.path.join(script_dir, "Pakkedump/styr-opptak.sh")
            kommando = f"{styr_opptak_path} start {avsender['navn']} {kanal}"

            if kanal == "Bluetooth":
                logging.info(f"Bluetooth blir sjekket for avsender {avsender['navn']}")
                input(f"{BOLD_GREEN}Aktiver HCI snoop logging i GUI på {avsender['navn']} før du fortsetter. Ikke åpne Briar! Trykk Enter når klar{RESET}")

            # Kjør kommandoen i bakgrunnen for alle kanalene
            run_zsh_command_background(kommando)


def liveonthree(avsendere):

    for avsender in avsendere:
        kanaler = avsender["kanaler"]
        
        if "WiFi" in kanaler or "Tor" in kanaler:
            logging.critical(f"Pinger fra {avsender['navn']} som startskudd... LIVE!")
            ping_hostname = os.path.join(script_dir, "../ressurser/ping_hostname.sh")
            hostname = "google.no"
            nPackets = 10
            kommando = f"{ping_hostname} {avsender['navn']} {hostname} {nPackets}"
            run_zsh_command_background(kommando)
        
        if "Bluetooth" in kanaler:
            logging.critical(f"Restarter bt på {avsender['navn']} som startskudd... LIVE!")
            bt_liveonthree = os.path.join(script_dir, "../ressurser/bt_liveonthree.sh")
            kommando = f"{bt_liveonthree} {avsender['navn']}"
            run_zsh_command_background
            (kommando)


def start_briar_og_logg_inn(avsendere):
    
    for avsender in avsendere:
        logging.debug(f"Avsender: {avsender['navn']}")

        # Sjekk enhetsnavn og hent device_id
        get_device_id_kommando = f"hent_enhets_id {avsender['navn']}"
        
        result = run_zsh_command(get_device_id_kommando)
        logging.debug(result)
        
        # Sjekk om result er None før vi går videre
        if result is None:
            logging.error(f"Kommando mislyktes: {get_device_id_kommando}. Ingen resultat returnert.")
            enhets_id = None
        elif not hasattr(result, 'stdout') or not result.stdout:
            logging.error(f"Feil: Ingen stdout returnert fra kommandoen for {avsender['navn']}")
            enhets_id = None
        else:
            enhets_id = result.stdout.strip()

        if enhets_id and result.returncode == 0:
            logging.info(f"Enhet-ID for {avsender['navn']}: {enhets_id} :)")
        else:
            enhets_id = None
            logging.error(f"Kunne ikke hente enhets-ID for {avsender['navn']}")
        
        logging.debug(f"Enhet-ID for {avsender['navn']}: {enhets_id}")

        if enhets_id:
            er_briar_aktiv = f"er_briar_aktiv {enhets_id}"
            logging.info(f"Kjører er_briar_aktiv for avsender: {avsender['navn']}")
            result = run_zsh_command(er_briar_aktiv)

            logging.debug(result)

            # Håndter resultatet basert på om det returneres en PID
            if result and result.stdout.strip():  # Hvis PID returneres
                briar_pid = result.stdout.strip()
                logging.warning(f"Briar er allerede aktiv på enhet {avsender['navn']} (PID: {briar_pid}), ingen handling nødvendig.")
            else:
                logging.warning(f"Briar er ikke aktiv på enhet {avsender['navn']}, starter Briar og logger inn...")
                logg_inn_briar = f"logg_inn_briar {avsender['navn']}"
                run_zsh_command(logg_inn_briar)

def toggle_kanal(avsendere, situasjonsnummer):
    
    for avsender in avsendere:
        logging.debug(f"Avsender: {avsender['navn']}")
        logging.debug(f"{avsender['navn']} sine kanaler: {avsender['kanaler']}")

        for kanal in avsender['kanaler']:
            if situasjonsnummer == 7 and avsender['navn'] == "Alice" and kanal == "Tor":
                logging.info(f"Hopper over å toggle Tor-kanal for {avsender['navn']} i situasjon 7.")
                continue
            kommando = f"toggle_kanal {avsender['navn']} {kanal}"
            logging.warning(f"Toggler kanal {kanal} on/off for avsender {avsender['navn']}")
            run_zsh_command(kommando)


def toggle_kanal_off(avsendere, situasjonsnummer):

    for avsender in avsendere:

        for kanal in avsender['kanaler']:
            if situasjonsnummer == 7 and avsender['navn'] == "Alice" and kanal == "Tor":
                logging.info(f"Hopper over å toggle Tor-kanal for {avsender['navn']} i situasjon 7.")
                continue
            
            kommando = f"toggle_kanal {avsender['navn']} {kanal}"
            logging.warning(f"Toggler kanal {kanal} on/off for avsender {avsender['navn']}")
            run_zsh_command(kommando)


def velg_samtale_sit_1_3(avsendere):
    
    for avsender in avsendere:
        logging.debug(f"Avsender: {avsender['navn']}")

        # Sjekk enhetsnavn og hent device_id
        kommando = f"velg_samtale_sit_1_3 {avsender['navn']}"
        logging.warning(f"velg_samtale_sit_1_3 for {avsender['navn']}")
        run_zsh_command(kommando)


def velg_samtale_4(avsendere):
    
    for avsender in avsendere:
        logging.debug(f"Avsender: {avsender['navn']}")

        # Sjekk enhetsnavn og hent device_id
        kommando = f"velg_samtale_sit_4 {avsender['navn']}"
        logging.warning(f"velg_samtale_sit_4 for {avsender['navn']}")
        run_zsh_command(kommando)


def send_meldinger(situasjonsnummer):    
    send_meldinger_path = os.path.join(script_dir, "send-meldinger.sh")
    kommando = f"{send_meldinger_path} en {situasjonsnummer}"
    logging.warning(f"Kjører send-meldinger for situasjon {situasjonsnummer}")
    run_zsh_command(kommando)
    

def stopp_pakkedumper(avsendere):
    styr_opptak_path = os.path.join(script_dir, "Pakkedump/styr-opptak.sh")
    
    for avsender in avsendere:
        kanaler = avsender["kanaler"]
        logging.info(f"Avsender {avsender['navn']} sine kanaler: {kanaler}")

        for kanal in kanaler:
            if kanal == "Tor" or kanal == "WiFi":
                kommando = f"{styr_opptak_path} stopp {avsender['navn']} {kanal}"
                logging.info(f"Stopper all pakkedump for {avsender['navn']}, kanal: {kanal}")
                run_zsh_command(kommando)

            if kanal == "Bluetooth":
                input(f"{BOLD_GREEN}Skru av HCI snoop logg i GUI for {avsender['navn']}. GÅ TILBAKE TIL BRIAR OG trykk Enter for å fortsette...{RESET}")
                kommando = f"{styr_opptak_path} stopp {avsender['navn']} {kanal}"
                logging.info(f"Stopper all pakkedump for {avsender['navn']}, kanal: {kanal}")
                run_zsh_command(kommando)


def stopp_briar(avsendere):
    
    for avsender in avsendere:
        logging.debug(f"Avsender: {avsender['navn']}")

        # Sjekk enhetsnavn og hent device_id
        get_device_id_kommando = f"hent_enhets_id {avsender['navn']}"
        
        result = run_zsh_command(get_device_id_kommando)
        logging.debug(result)
        
        enhets_id = result.stdout.strip()

        if result and result.returncode == 0:
            logging.info(f"Enhet-ID for {avsender['navn']}: {enhets_id} :)")
        else:
            enhets_id = None
            logging.error(f"Kunne ikke hente enhets-ID for {avsender['navn']}")
        
        logging.debug(f"Enhet-ID for {avsender['navn']}: {enhets_id}")

        er_briar_aktiv = f"er_briar_aktiv {enhets_id}"
        logging.info(f"Kjører er_briar_aktiv for avsender: {avsender['navn']}")
        result = run_zsh_command(er_briar_aktiv)

        logging.debug(result)

        if result.returncode == 0:
            logging.info(f"Briar er aktiv på enhet {avsender['navn']}, stopper Briar...")
            stopp_briar = f"stopp_briar {enhets_id}"
            run_zsh_command(stopp_briar)
        else:
            logging.warning(f"Briar er ikke aktiv på enhet {avsender['navn']}, ingen handling nødvendig...")


def hent_pakkedumper(avsendere, resultat_sti_for_pakkedump):
    for avsender in avsendere:
        pakkedump_dest = resultat_sti_for_pakkedump
        hent_pakkedump_path = os.path.join(script_dir, "Pakkedump/hent-pakkedumper.sh")
        kommando = f"{hent_pakkedump_path} {pakkedump_dest} {avsender['navn']}"
        logging.info(f"Kjører hent-pakkedumper for avsender: {avsender['navn']}")
        run_zsh_command(kommando)


def hent_lokallagring(avsendere, situasjonsnummer):
    for avsender in avsendere:
        hent_pakkedump_path = os.path.join(script_dir, "LokalLagring/hent-lokallagring.sh")
        kommando = f"{hent_pakkedump_path} {avsender['navn']} {situasjonsnummer} ./LokalLagring/kopier"
        logging.info(f"Kjører hent-lokallagring for avsender: {avsender['navn']}")
        run_zsh_command(kommando)


def sjekk_og_slett_tomme_mapper(sti):
    """Sjekker om mappen eksisterer og er tom. Hvis tom, slettes den."""
    if os.path.isdir(sti) and not os.listdir(sti):  # Sjekk om det er en mappe og om den er tom
        os.rmdir(sti)
        logging.info(f"Slettet tom mappe: {sti}")


def kopier_innhold_til_tor(sti, tor_dir):
    """Kopier innhold fra wifi-mappen til tor-mappen."""
    if os.path.exists(sti):
        if not os.path.exists(tor_dir):
            os.makedirs(tor_dir)

        for filename in os.listdir(sti):
            file_path = os.path.join(sti, filename)
            shutil.copy(file_path, tor_dir)

    else:
        logging.info(f"Mappen {sti} finnes ikke, kan ikke kopiere innhold.")



def flytt_innhold_til_tor(sti, tor_dir):
    """Flytt innhold fra wifi-mappen til tor-mappen."""
    if os.path.exists(sti):
        if not os.path.exists(tor_dir):
            os.makedirs(tor_dir)

        for filename in os.listdir(sti):
            file_path = os.path.join(sti, filename)
            shutil.move(file_path, tor_dir)

        # Slett WiFi-mappen etter at innholdet er flyttet
        os.rmdir(sti)
        logging.info(f"Slettet mappen: {sti} etter å ha flyttet filer til {tor_dir}.")
    else:
        logging.info(f"Mappen {sti} finnes ikke, kan ikke flytte innhold.")


def kopier_innhold_til_tor(sti, tor_dir):
    """Kopier innhold fra wifi-mappen til tor-mappen."""
    if os.path.exists(sti):
        if not os.path.exists(tor_dir):
            os.makedirs(tor_dir)

        for filename in os.listdir(sti):
            file_path = os.path.join(sti, filename)
            shutil.copy(file_path, tor_dir)

        logging.info(f"Kopierte innhold fra {sti} til {tor_dir}. Ingen filer slettet.")
    else:
        logging.info(f"Mappen {sti} finnes ikke, kan ikke kopiere innhold.")


def restart_enhet(avsendere):
    for avsender in avsendere:
        logging.critical(f"Restarter enhet {avsender['navn']}")
        kommando = f"restart_enhet {avsender['navn']}"
        run_zsh_command(kommando)


def main(datasett_sti, situasjons_nummer, test, restart):
    logger = logging.getLogger()
    
    logger.info(f"Starter program med datasett: {datasett_sti} og situasjonsnummer: {situasjons_nummer}")


    iso_time = datetime.now().isoformat(timespec='seconds').replace(':', '-')
    resultat_sti_for_pakkedump = os.path.join(script_dir, f"Pakkedump/situasjons_pakkedumper/situasjon_{situasjons_nummer}/{iso_time}")
    logger.info(f"Her kommer resultatene: {resultat_sti_for_pakkedump}")

    if not os.path.exists(resultat_sti_for_pakkedump):
        os.makedirs(resultat_sti_for_pakkedump)

    data = les_datasett(datasett_sti, situasjons_nummer)

    avsendere = data["avsendere"]

    # Trinn 0 - backup i tilfelle noen henger fra tidligere
    if restart:
        restart_enhet(avsendere)
        time.sleep(120)
        liveonthree(avsendere)

    hent_pakkedumper_alle(avsendere)
    
    # Trinn 1
    slett_pakkedumper(avsendere)

    # Trinn 1.5
    lukk_briar(avsendere)

    # Trinn 2
    start_pakkedumper(avsendere)
    time.sleep(1)
    start_briar_og_logg_inn(avsendere)
    time.sleep(10)

    # Trinn 4
    logging.error("Påse at riktig kanal velges for situasjonen!")
    situasjons_nummer = int(situasjons_nummer)  # Convert situasjons_nummer to an integer
    
    toggle_kanal(avsendere, situasjons_nummer)
    if situasjons_nummer == 1:
        deltakere = [
            {'navn': 'Alice'},
            {'navn': 'Bob'},
            {'navn': 'Charlie'},
            {'navn': 'Dave'}
        ]
        hent_lokallagring(deltakere, situasjons_nummer-1)

    if situasjons_nummer < 4:
        velg_samtale_sit_1_3(avsendere)

    if situasjons_nummer == 4:
        logging.critical(f"Velg riktig samtale (StudyGroup !!) for situasjon {situasjons_nummer} manuelt!")
        time.sleep(5)
        velg_samtale_4(avsendere) # funker bare første gang? pga. nyeste øverst?

    if situasjons_nummer == 5:
        logging.critical(f"Velg riktig samtale (Neighborhood !!) for situasjon {situasjons_nummer} manuelt!")
        time.sleep(5)
        velg_samtale_4(avsendere) # funker bare første gang? pga. nyeste øverst? Funker ev. på den sist opprettede samtalen.

    if situasjons_nummer == 6:
        logging.critical(f"Velg riktig samtale (EchoChamber !!) for situasjon {situasjons_nummer} manuelt!")
        time.sleep(5)

    if situasjons_nummer == 7:
        logging.critical(f"Velg riktig samtale (Blog !!) for situasjon {situasjons_nummer} manuelt!")
        time.sleep(5)


    # Trinn 3
    if test:
        kontroll=0.5
    else:
        kontroll=10*60

    logging.warning(f"Starter venting i {kontroll/60} minutter for en adekvat kontrolldump... Bruk tiden til å sjekke at alt er som det skal.")

    if test:
        logging.warning("Testmodus aktivert; Kort venting og ingen nedtelling")
        time.sleep(kontroll)
    else:
        for remaining in range(int(kontroll), 0, -1):
            if remaining % 30 == 0:
                logging.warning(f"Venter: {remaining} sekunder igjen.")
            time.sleep(1)
        logging.warning("Venter: Ferdig.")

    logging.warning("Ferdig venting. Fortsetter programmet...")

    # Trinn 3.5
    liveonthree(avsendere)
    time.sleep(20)
    send_meldinger(situasjons_nummer)

    # Trinn 4.1
    time.sleep(30)
    stopp_pakkedumper(avsendere)

    # Trinn 4.2
    time.sleep(1)
    toggle_kanal_off(avsendere, situasjons_nummer)
    
    stopp_briar(avsendere)

    # Trinn 5
    hent_pakkedumper(avsendere, resultat_sti_for_pakkedump)
    slett_pakkedumper(avsendere)
    hent_lokallagring(avsendere, situasjons_nummer)

    logger.warning("Ferdig med situasjonen.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Les datasett og finn avsendere og kanaler for en spesifikk situasjon.")
    parser.add_argument('-d', '--datasett_sti', type=str, required=True, help="Sti til datasett CSV-filen.")
    parser.add_argument('-s', '--situasjonsnummer', type=str, required=True, help="Situasjonsnummeret for å filtrere datasettet.")
    parser.add_argument('-t', '--test', action='store_true', help="Reduser ventetid for testing")
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Øk verbose nivå: -v for INFO, -vv for DEBUG")
    parser.add_argument('-r', '--restart', action='store_true', help="Restart enhetene")


    args = parser.parse_args()

    logger = setup_logger(args.verbose)

    main(args.datasett_sti, args.situasjonsnummer, args.test, args.restart)
