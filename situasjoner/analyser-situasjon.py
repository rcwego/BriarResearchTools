import sys
import os
import json
import argparse
import logging
import re
import glob
import fnmatch
import pyshark
import math
import time
from datetime import datetime
import shutil
import zlib
import csv
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ressurser')))
from custom_formatter import CustomFormatter, RESET, YELLOW, RED, BOLD_GREEN, BOLD_RED
from hjelpe_funksjoner import beregn_entropi, beregn_kompresjonsgrad


# Funksjon for å sette opp loggeren
def setup_logger(log_filbane, verbose_level):

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Alltid logg DEBUG til filen

    # Filhandler (Logger alle nivåer til fil)
    file_handler = logging.FileHandler(log_filbane)
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

# Klasse for Kanal
class Kanal:
    def __init__(self, navn, sti, pcap_fil, csv_fil, situasjon, logger):
        self.navn = navn
        self.sti = sti
        self.pcap_fil = os.path.join(sti, pcap_fil)
        self.csv_fil = csv_fil
        self.situasjon = situasjon
        self.situasjonsnummer = self.situasjon.nummer
        self.avsendere = self.situasjon.avsendere
        self.mac = None
        self.ip = None
        self.bytes_totalt = None
        self.payload_packets = None
        self.tor_iper = [] if navn == 'tor' else None
        self.localhost_tor_porter = [] if navn == 'tor' else None
        self.internett_tor_porter = [] if navn == 'tor' else None
        self.entropi = None
        self.kompresjonsrate = None
        self.funnet_hele_meldinger = None
        self.funnet_uuid = None
        self.funnet_emneknagg = None
        self.funnet_kallenavn = None
        self.funnet_kryptografiske_artefakter = None
        self.tilknyttet_kanal = None
        self.logger = logger
        self.parse_meta_files()

    # Funksjon for å trekke ut nyttig info fra meta-filer
    def parse_meta_files(self):
        btmac_file = glob.glob(os.path.join(self.sti, '*-bt-mac.txt'))
        wlan0_ip_file = glob.glob(os.path.join(self.sti, '*-wlan0-ip.txt'))
        wlan0_mac_file = glob.glob(os.path.join(self.sti, '*-wlan0-mac.txt'))
        tor_sockets_files = glob.glob(os.path.join(self.sti, '*-tor-sockets.txt'))

        if btmac_file:
            self.mac = self.les_fil_innhold(btmac_file[0])
            self.logger.debug(f"Bluetooth MAC-adresse fra {btmac_file[0]}: {self.mac}")
        if wlan0_ip_file:
            self.ip = self.les_fil_innhold(wlan0_ip_file[0])
            self.logger.debug(f"WiFi IP-adresse fra {wlan0_ip_file[0]}: {self.ip}")
        if wlan0_mac_file:
            self.mac = self.les_fil_innhold(wlan0_mac_file[0])
            self.logger.debug(f"WiFi MAC-adresse fra {wlan0_mac_file[0]}: {self.mac}")
        if tor_sockets_files:
            self.localhost_tor_porter, self.internett_tor_porter = self.hent_tor_porter(tor_sockets_files)
            self.localhost_tor_porter = list(self.localhost_tor_porter)
            self.internett_tor_porter = list(self.internett_tor_porter)
            self.tor_iper = self.hent_tor_iper(tor_sockets_files)


    def les_fil_innhold(self, filnavn):
        try:
            with open(filnavn, 'r') as f:
                innhold = f.read().strip()
                self.logger.debug(f"Innhold i {filnavn}: {innhold}")
                return innhold
        except FileNotFoundError:
            self.logger.warning(f"{self.navn} Fil ikke funnet: {filnavn}")
            return None
        

    # Funksjon for å analysere tor-sockets-filer
    def hent_tor_porter(self, tor_sockets_files):
        sockets = set()
        localhost_tor_porter = set()
        internett_tor_porter = set()
        pattern = re.compile(r'127\.0\.0\.1:(\d+)')

        for filbane in tor_sockets_files:
            with open(filbane, 'r') as fil:
                linjer = fil.readlines()
                for linje in linjer:
                    if 'tor' in linje:
                        # Legger til linjen i internett_tor_porter direkte
                        sockets.add(linje)
                        
                        # Finn alle matcher for localhost
                        matches = pattern.findall(linje)
                        if len(matches) == 2:  # Både kilde og destinasjon må matche
                            localhost_tor_porter.add(matches[0])
                            localhost_tor_porter.add(matches[1])
        
        for element in sockets:
            self.logger.debug(element.strip())

        self.logger.debug(f"Tor IP-er fra {tor_sockets_files}: {list(internett_tor_porter)}")
        self.logger.debug(f"127.0.0.1 Ports fra {tor_sockets_files}: {list(localhost_tor_porter)}")
        return localhost_tor_porter, internett_tor_porter


    def hent_tor_iper(self, filbaner):
        tor_iper = set()  # Bruker set i stedet for liste for å unngå duplikater
        for filnavn in filbaner:
            try:
                with open(filnavn, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+):443', line)
                        if match:
                            tor_iper.add(match.group(1))  # Legger til i set
                self.logger.debug(f"Tor IP-adresser hentet fra {filnavn}: {tor_iper}")
            except FileNotFoundError:
                self.logger.warning(f"{self.navn}: Tor-fil ikke funnet: {filnavn}")
        return list(tor_iper)  # Konverterer set til liste før retur



    def __repr__(self):
        return f"Kanal(navn={self.navn}, pcap_fil={self.pcap_fil}, mac={self.mac}, ip={self.ip}, tor_iper={self.tor_iper}), localhost_tor_porter={self.localhost_tor_porter}, internett_tor_porter={self.internett_tor_porter})"

    def analyser_kanal(self):
        if self.navn == 'wifi':
            payloads = self.analyser_wifi()
        
        elif self.navn == 'tor':
            payloads = self.analyser_tor()

        elif self.navn == 'bt':
            payloads = self.analyser_blåtann()
        
        else:
            self.logger.warning(f"Ukjent kanaltype {self.navn}. Ingen analyse tilgjengelig.")


        if not isinstance(payloads, list):  # Sjekk at payloads er en liste
            self.logger.error(f"Ugyldig payloads-type: {type(payloads)} for kanal {self.navn}")
            return

        samlet_payload = b''.join(payloads)
        self.bytes_totalt = len(samlet_payload)  # Totalt antall bytes

        if self.bytes_totalt > 0:
            self.entropi = beregn_entropi(samlet_payload)
            self.kompresjonsrate = beregn_kompresjonsgrad(samlet_payload)
            self.logger.debug(f"Leser relevante meldinger fra {self.csv_fil} for situasjon {self.situasjonsnummer}")
            meldinger, uuider = les_meldinger_fra_csv(self)
            self.funnet_hele_meldinger = søk_etter_meldinger(self, samlet_payload, meldinger)
            self.funnet_uuid = søk_etter_uuid(self, samlet_payload, uuider)
            self.funnet_emneknagg = søk_etter_emneknagg(self, samlet_payload, "#NTNU-MISEB")
            self.funnet_kallenavn = søk_etter_kallenavn(self, samlet_payload)
            self.funnet_kryptografiske_artefakter = søk_etter_kryptografiskealgoritmer(self, samlet_payload)
        else:
            self.logger.warning(f"Ingen nyttelast funnet i kanal {self.navn}.")


    # Analyse for WiFi-kanaler
    def analyser_wifi(self):
        if not self.tilknyttet_kanal:
            self.logger.warning(f"Ingen tilknyttet kanal funnet for {self.navn}.")
            return
        if not self.ip or not self.tilknyttet_kanal.ip:
            self.logger.warning(f"Ingen gyldige IP-er funnet for {self.navn} eller den tilknyttede kanalen.")
            return

        ip_self = self.ip
        ip_tilknyttet = self.tilknyttet_kanal.ip
        self.logger.info(f"Bruker IP-adresser for pakkefiltrering: {ip_self} (self) og {ip_tilknyttet} (tilknyttet)")

        ip_src = {ip_self}
        ip_dst = {ip_tilknyttet}

        display_filter=f'ip.src == {ip_src} && ip.dst == {ip_dst}'
        capture = pyshark.FileCapture(self.pcap_fil, display_filter)
        self.logger.debug(f"Display filter for {self.navn}: {display_filter}")
        
        payloads = []
        self.payload_packets = 0
        for packet in capture:
            try:
                if hasattr(packet, 'tcp') and hasattr(packet.tcp, 'payload'):
                    raw_data = bytes.fromhex(packet.tcp.payload.replace(':', ''))
                    if raw_data:
                        payloads.append(raw_data)
                        self.payload_packets += 1
            except AttributeError:
                continue

        capture.close()
    
        return payloads


    def analyser_tor(self):
        self.logger.info(f"Analyserer kanal {self.navn} fra {self.pcap_fil} med lokal IP-adressefiltrering.")

        ip_src = "127.0.0.1"
        ip_dst = "127.0.0.1"

        if not self.localhost_tor_porter:
            self.logger.warning(f"Ingen localhost Tor-porter funnet for {self.navn}.")
            return

        tcp_ports_filter = ' || '.join([f'tcp.port == {port}' for port in self.localhost_tor_porter])
        display_filter = f'ip.src == {ip_src} && ip.dst == {ip_dst} && ({tcp_ports_filter})'
        capture = pyshark.FileCapture(self.pcap_fil, display_filter)
        self.logger.debug(f"Display filter for {self.navn}: {display_filter}")

        payloads = []
        self.payload_packets = 0

        for packet in capture:
            try:
                # Forsøk å hente nyttelast fra TCP-pakkene
                if hasattr(packet, 'tcp') and hasattr(packet.tcp, 'payload'):
                    raw_data = bytes.fromhex(packet.tcp.payload.replace(':', ''))
                    if raw_data:  # Hvis det er data i nyttelasten
                        payloads.append(raw_data)
                        self.payload_packets += 1  # Telle antall pakker med nyttelast
            except AttributeError:
                continue

        capture.close()

        return payloads


    # Analyse for Bluetooth-kanaler
    def analyser_blåtann(self):
        capture = pyshark.FileCapture(self.pcap_fil)
        payloads = []

        for pakke in capture:
            lag = [l.layer_name for l in pakke.layers]
            if 'btl2cap' in lag and 'btrfcomm' in lag:
                try:
                    if hasattr(pakke, 'data'):
                        payload = bytes.fromhex(pakke.data.data.replace(':', ''))
                        
                        if payload:  # Sørg for at det er nyttelast før det legger det til
                            payloads.append(payload)
                
                except Exception as e:
                    self.logger.warning(f"Feil ved parsing av pakke {pakke.number}: {e}")

        capture.close()

        return payloads


# Funksjon for å søke etter kjente kryptografiske_artefakter i samlet_payload
def søk_etter_kryptografiskealgoritmer(self, samlet_payload):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_kryptografiske_artefakter = []
    kryptografiske_algoritmer = ['AES', 'EC25519', 'ECDH', 'HMAC', 'SHA256', 'ED25519', 'X25519', 'H2', 'ECDSA', 'H2encrypt'] # TEST
    kryptografiske_nøkkelord = ['encrypt', 'decrypt', 'sign', 'verify', 'key exchange', 'hash', 'cipher', 'salt', 'nonce', 'IV', 'symmetric', 'asymmetric', 'public key', 'private key', 'encrypted'] # TEST
    tor_nøkkelord = ['onion']

    kombinertliste = kryptografiske_algoritmer + kryptografiske_nøkkelord + tor_nøkkelord

    for algoritme in kombinertliste:
        self.logger.debug(f"Søker etter kryptografiske artefakter: {algoritme}")

        if algoritme in samlet_payload_str:
            funnet_kryptografiske_artefakter.append(algoritme)
            self.logger.warning(f"{self.navn}: Funnet kryptografiske artefakt: {algoritme}")

    if not funnet_kryptografiske_artefakter:
        self.logger.info(f"Ingen kryptografiske artefakter funnet i {self.navn}.")
        return False
    
    return funnet_kryptografiske_artefakter

# Funksjon for å søke etter meldinger i pakkedumpene
def søk_etter_meldinger(self, samlet_payload,  meldinger):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_hele_meldinger = []


    for melding_nummer, melding in enumerate(meldinger, start=1):
        self.logger.debug(f"Søker etter melding {melding_nummer}: {melding}")
        if melding in samlet_payload_str:
            funnet_hele_meldinger.append(melding)
            self.logger.warning(f"Funnet melding {melding_nummer}: {melding}")

    if not funnet_hele_meldinger:
        self.logger.info(f"Ingen hele meldinger funnet i {self.navn}.")
        return False
    
    return funnet_hele_meldinger


# Funksjon for å søke etter meldinger i pakkedumpene
def søk_etter_uuid(self, samlet_payload, uuider):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_uuid = []

    for uuid_nummer, uuid in enumerate(uuider, start=1):
        self.logger.debug(f"Søker etter uuid {uuid_nummer}: {uuid}")
        if uuid in samlet_payload_str:
            funnet_uuid.append(uuid)
            self.logger.warning(f"Funnet uuid {uuid_nummer}: {uuid}")

    if not funnet_uuid:
        self.logger.info(f"Ingen UUID-er funnet i {self.navn}.")
        return False
    
    return funnet_uuid


# Funksjon for å søke etter meldinger i pakkedumpene
def søk_etter_emneknagg(self, samlet_payload, emneknagg):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_emneknagg = False

    self.logger.debug(f"Søker etter emneknagg: {emneknagg} i samlet_payload_str:\n{samlet_payload_str}")
    if emneknagg in samlet_payload_str:
        funnet_emneknagg = True
        self.logger.warning(f"Funnet emneknagg {emneknagg} i samlet_payload_str!!!")

    if not funnet_emneknagg:
        self.logger.info(f"Ingen emneknagg funnet i {self.navn}.")
        return False
    
    return funnet_emneknagg

# Funksjon for å søke etter meldinger i pakkedumpene
def søk_etter_kallenavn(self, samlet_payload):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_kallenavn = []

    for kallenavn in self.avsendere:
        kallenavn_str = kallenavn.navn
        self.logger.debug(f"Søker etter kallenavn: {kallenavn_str} i samlet_payload_str")

        if kallenavn_str in samlet_payload_str:
            funnet_kallenavn.append(kallenavn_str)
            self.logger.warning(f"Funnet kallenavn: {kallenavn_str} i samlet_payload_str!!!")

    if not funnet_kallenavn:
        self.logger.info(f"Ingen kallenavn funnet i {self.navn}.")
        return False
    
    return funnet_kallenavn


# Felles hjelpefunksjon for å lese relevante meldinger fra datasett
def les_meldinger_fra_csv(self):
    meldinger = []
    uuider = []
    try:
        with open(self.csv_fil, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row_num, row in enumerate(reader, start=1):
                # Filtrer meldinger basert på "Situasjon" som matcher situasjonsnummeret
                if int(row['Situasjon']) == self.situasjonsnummer:
                    meldinger.append(row['Melding'])
                    self.logger.debug(f"Situasjon {self.situasjonsnummer}, Melding {(row_num - 1) % 50 + 1}: {row['Melding']}")
                    
                    uuider.append(row['UUID'])
                    self.logger.debug(f"Situasjon {self.situasjonsnummer}, Melding {(row_num - 1) % 50 + 1}: {row['UUID']}")
    except FileNotFoundError:
        self.logger.warning(f"CSV-fil ikke funnet: {self.csv_fil}")
    except KeyError:
        self.logger.warning(f"Kolonnen 'Melding' eller 'Situasjon' mangler i CSV-filen.")
    return meldinger, uuider


class Avsender:
    def __init__(self, navn):
        self.navn = navn
        self.kanaler = []  # Kanaler som avsender er en del av

    def legg_til_kanal(self, kanal):
        self.kanaler.append(kanal)

    def til_json(self):
        return {
            "navn": self.navn,
            "kanaler": [kanal.til_json() for kanal in self.kanaler]
        }

    def __repr__(self):
        return f"Avsender(navn={self.navn}, kanaler={self.kanaler})"


class Situasjon:
    def __init__(self, nummer, timestamp):
        self.nummer = nummer
        self.timestamp = timestamp
        self.avsendere = []

    def legg_til_avsender(self, avsender):
        self.avsendere.append(avsender)

    # JSON-serialisering uten avsendernavn for tilknyttet kanal
    def til_json(self):
        return {
            "situasjonsnummer": self.nummer,
            "iso_timestamp": self.timestamp,
            "avsendere": [
                {
                    "navn": avsender.navn,
                    "kanaler": [
                        {
                            "navn": kanal.navn,
                            "pcap_fil": kanal.pcap_fil,
                            "mac": kanal.mac,
                            "funnet_hele_meldinger": kanal.funnet_hele_meldinger,
                            "funnet_uuid": kanal.funnet_uuid,
                            "funnet_emneknagg": kanal.funnet_emneknagg,
                            "funnet_kallenavn": kanal.funnet_kallenavn,
                            "funnet_kryptografiske_artefakter": kanal.funnet_kryptografiske_artefakter,
                            "entropi": kanal.entropi,
                            "kompresjonsrate": kanal.kompresjonsrate,
                            "bytes_totalt": kanal.bytes_totalt,
                            "payload_packets": kanal.payload_packets,
                            **({"ip": kanal.ip} if kanal.ip is not None and kanal.navn != 'bt' else {}),
                            **({"tor_iper": kanal.tor_iper} if kanal.navn == 'tor' else {}),
                            **({"localhost_tor_porter": kanal.localhost_tor_porter} if kanal.navn == 'tor' else {}),
                            **({"internett_tor_porter": kanal.internett_tor_porter} if kanal.navn == 'tor' else {}),
                            **({"tilknyttet_kanal": {
                                    "navn": kanal.tilknyttet_kanal.navn,
                                    "pcap_fil": kanal.tilknyttet_kanal.pcap_fil,
                                    "mac": kanal.tilknyttet_kanal.mac,
                                    **({"ip": kanal.tilknyttet_kanal.ip} if kanal.tilknyttet_kanal.ip else {}),
                                    **({"tor_iper": kanal.tilknyttet_kanal.tor_iper} if kanal.tilknyttet_kanal.navn == 'tor' else {})
                                }} if kanal.tilknyttet_kanal else {})
                        } for kanal in avsender.kanaler
                    ]
                } for avsender in self.avsendere
            ]
        }

    def __repr__(self):
        return f"Situasjon(nummer={self.nummer}, timestamp={self.timestamp}, , situasjonsnummer={self.situasjonsnummer}, avsendere={self.avsendere})"


# Funksjon for å filtrere skjulte filer og mapper
def filtrer_skjulte_filer(filer_liste):
    return [fil for fil in filer_liste if not fil.startswith('.')]


# Funksjon for å lese situasjonen basert på filstruktur
def les_situasjon(situasjonsnummer, base_dir, csv_fil, logger):
    situasjons_sti = os.path.join(base_dir, f"situasjon_{situasjonsnummer}")
    
    # Finn den nyeste mappen basert på timestamp, ignorer skjulte mapper
    synlige_mapper = filtrer_skjulte_filer(os.listdir(situasjons_sti))
    nyeste_mappe = max([os.path.join(situasjons_sti, d) for d in synlige_mapper], key=os.path.getmtime)
    iso_timestamp = os.path.basename(nyeste_mappe)

    logger.info(f"Nyeste mappe for situasjon {situasjonsnummer} er {iso_timestamp}")
    
    situasjon = Situasjon(situasjonsnummer, iso_timestamp)

    # Les avsendere og deres kanaler, ignorer skjulte mapper
    avsender_mappene = filtrer_skjulte_filer(os.listdir(nyeste_mappe))
    for avsender_navn in avsender_mappene:
        avsender_sti = os.path.join(nyeste_mappe, avsender_navn)
        if os.path.isdir(avsender_sti):
            avsender = Avsender(avsender_navn)

            # Tre mulige kanaler: 'bt', 'wifi', 'tor'
            for kanal_navn in ['bt', 'wifi', 'tor']:
                kanal_sti = os.path.join(avsender_sti, kanal_navn)
                if os.path.isdir(kanal_sti):  # Hvis kanalens mappe eksisterer

                    # Bruk fnmatch for case-insensitive mønstersjekk
                    is_file_pattern = f'*is-{kanal_navn}.txt'
                    finnes_is_fil = any(fnmatch.fnmatchcase(filnavn.lower(), is_file_pattern.lower()) for filnavn in os.listdir(kanal_sti))
                    logger.debug(f"Finnes IS-fil for {kanal_navn}: {finnes_is_fil}")

                    if not finnes_is_fil:
                        logger.info(f"Sletter irrelevante resultater i {kanal_sti}")
                        shutil.rmtree(kanal_sti)
                        logger.info(f"Mappen {kanal_sti} og alt innhold er slettet.")
                        continue

                    # Sjekk etter .pcap eller .pcapng filer for kanalen
                    pcap_filer = filtrer_skjulte_filer(
                        [f for f in os.listdir(kanal_sti) if f.endswith('.pcap') or f.endswith('.pcapng')]
                    )

                    if pcap_filer:  # Hvis det finnes en pakkefil
                        nyeste_pcap_fil = max(pcap_filer, key=lambda f: os.path.getmtime(os.path.join(kanal_sti, f)))
                        eldste_pcap_fil = min(pcap_filer, key=lambda f: os.path.getmtime(os.path.join(kanal_sti, f)))
                        logger.debug(f"Nyeste pcap-fil: {nyeste_pcap_fil}")
                        logger.debug(f"Eldste pcap-fil: {eldste_pcap_fil}")
                        
                        pcap_fil = nyeste_pcap_fil
                        logger.info(f"Bruker pakkefil: {pcap_fil} for kanal {kanal_navn}")

                        kanal = Kanal(kanal_navn, kanal_sti, pcap_fil, csv_fil, situasjon, logger)
                        avsender.legg_til_kanal(kanal)
                    else:
                        # Hvis ingen pcap/pcapng-filer finnes, logg en advarsel
                        logger.error(f"Ingen pcap eller pcapng filer funnet i {kanal_sti} for {kanal_navn}. "
                                     f"Konverter manuelt fra .log til .pcapng og prøv igjen.")

            situasjon.legg_til_avsender(avsender)

    # Lagre situasjonen som JSON
    json_fil = os.path.join(nyeste_mappe, f'{iso_timestamp}-situasjon_{situasjonsnummer}_analyse.json')
    with open(json_fil, 'w') as f:
        json.dump(situasjon.til_json(), f, indent=4)
    
    logger.info(f"Situasjonsdata lagret i: {json_fil}")

    return situasjon



def koble_sammen_kanaler(situasjon, logger):
    for avsender in situasjon.avsendere:
        for kanal in avsender.kanaler:
            for annen_avsender in situasjon.avsendere:
                if annen_avsender.navn != avsender.navn:
                    for annen_kanal in annen_avsender.kanaler:
                        if annen_kanal.navn == kanal.navn:
                            kanal.tilknyttet_kanal = annen_kanal
                            annen_kanal.tilknyttet_kanal = kanal
                            logger.info(f"Kobler {kanal.navn} fra {avsender.navn} med {annen_kanal.navn} fra {annen_avsender.navn}")



def main():
    parser = argparse.ArgumentParser(description="Analyser situasjoner og generer rapporter.")
    parser.add_argument('-s', '--situasjon', type=int, required=True, help='Situasjonsnummeret som skal analyseres')
    parser.add_argument('-d', '--base_dir', type=str, default='./situasjons_pakkedumper', help='Base directory for situasjonene')
    parser.add_argument('-c', '--csv_fil', type=str, default='./../Datasett/datasett_en_med_uuids.csv', help='Filbane til CSV-filen med meldinger')
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Øk verbose nivå: -v for INFO, -vv for DEBUG")

    args = parser.parse_args()

    # Finn den nyeste situasjonsmappen og bestem loggfil- og json-filbanene
    situasjons_sti = os.path.join(args.base_dir, f"situasjon_{args.situasjon}")
    synlige_mapper = filtrer_skjulte_filer(os.listdir(situasjons_sti))
    nyeste_mappe = max([os.path.join(situasjons_sti, d) for d in synlige_mapper], key=os.path.getmtime)
    iso_timestamp = os.path.basename(nyeste_mappe)

    # Sett opp loggeren til å lagre loggfilen i samme mappe som JSON-filen
    log_filbane = os.path.join(nyeste_mappe, f'{iso_timestamp}-situasjon_{args.situasjon}_analyse.log')
    logger = setup_logger(log_filbane, args.verbose)

    logger.info(f"Starter analyse for situasjon {args.situasjon} med base_dir {args.base_dir} og CSV-fil {args.csv_fil}")

    # Les og analyser situasjonen
    situasjon = les_situasjon(args.situasjon, args.base_dir, args.csv_fil, logger)

    # Koble sammen motstående kanaler
    koble_sammen_kanaler(situasjon, logger)

    # Beregn entropi og komprimeringsgrad for hver kanal
    for avsender in situasjon.avsendere:
        for kanal in avsender.kanaler:
            kanal.analyser_kanal()

    # Print JSON-objektet til skjermen
    json_data = situasjon.til_json()
    print(json.dumps(json_data, indent=4))

    # Lagre situasjonen som JSON etter entropiberegning
    json_fil = os.path.join(nyeste_mappe, f'{iso_timestamp}-situasjon_{args.situasjon}_analyse.json')
    with open(json_fil, 'w') as f:
        json.dump(json_data, f, indent=4)

    logger.info(f"Situasjonsdata lagret i: {json_fil}")




if __name__ == "__main__":
    main()
