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
from hjelpe_funksjoner import beregn_entropi, beregn_entropi_original_datasett, beregn_kompresjonsgrad


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


# Felles hjelpefunksjon for å lese relevante meldinger fra datasett
def les_meldinger_fra_csv(csv_fil, logger):
    meldinger = []
    try:
        with open(csv_fil, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row_num, row in enumerate(reader, start=1):
                    meldinger.append(row['Melding'])
                    
        
    except FileNotFoundError:
        logger.warning(f"CSV-fil ikke funnet: {csv_fil}")
    except KeyError:
        logger.warning(f"Kolonnen 'Melding' eller 'Situasjon' mangler i CSV-filen.")
    return meldinger


def main():
    parser = argparse.ArgumentParser(description="Analyser situasjoner og generer rapporter.")
    parser.add_argument('-c1', '--csv_fil1', type=str, default='./../Datasett/datasett_en_med_uuids.csv', help='Filbane til CSV-filen med meldinger')
    parser.add_argument('-c2', '--csv_fil2', type=str, default='./../Datasett/datasett_en.csv', help='Filbane til CSV-filen med meldinger')
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Øk verbose nivå: -v for INFO, -vv for DEBUG")

    args = parser.parse_args()

    # Sett opp loggeren til å lagre loggfilen i samme mappe som JSON-filen
    log_filbane = os.path.join(os.path.dirname(args.csv_fil1), 'analyser-original-datasett.log')
    logger = setup_logger(log_filbane, args.verbose)
    meldinger1 = les_meldinger_fra_csv(args.csv_fil1, logger)
    meldinger2 = les_meldinger_fra_csv(args.csv_fil2, logger)
    
    # Beregn entropi og kompresjonsgrad for alle meldingene
    entropi1 = beregn_entropi_original_datasett(meldinger1)
    entropi2 = beregn_entropi_original_datasett(meldinger2)

    joined_data = ''.join(meldinger1).encode('utf-8')
    kompresjonsgrad = beregn_kompresjonsgrad(joined_data)
    
    logger.warning(f"Entropi med uuids: {entropi1}")
    logger.warning(f"Entropi uten uuids: {entropi2}")
    logger.warning(f"Kompresjonsgrad med uuids: {kompresjonsgrad}")


if __name__ == "__main__":
    main()
