import jaydebeapi
import argparse
import logging
import os
import sys
import json
import re
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ressurser')))
from custom_formatter import CustomFormatter
from hjelpe_funksjoner import beregn_entropi, beregn_kompresjonsgrad, les_meldinger_fra_csv, søk_etter_uuid, søk_etter_meldinger, søk_etter_emneknagg, søk_etter_kallenavn, søk_etter_kryptografiskealgoritmer

def setup_logger(verbose_level):
    log_dir = './log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    script_navn = os.path.splitext(os.path.basename(__file__))[0]
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    log_filnavn = f'{script_navn}-{timestamp}.log'
    log_file = os.path.join(log_dir, log_filnavn)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

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

def les_h2_database(database_path):
    h2_jar = "../../ressurser/h2-2.3.232.jar"
    h2_url = f"jdbc:h2:file:{database_path}"

    logging.info(f"Kobler til H2-databasen på {database_path}")
    conn = jaydebeapi.connect("org.h2.Driver", h2_url, ["", ""], h2_jar)

    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='PUBLIC'")
    tabeller = cursor.fetchall()

    if not tabeller:
        logging.warning(f"Ingen tabeller funnet i databasen: {database_path}")
        return None

    logging.info(f"Fant følgende tabeller: {tabeller}")
    logging.info(f"Tabeller i databasen: {tabeller}")

    # Bytt til riktig tabellnavn
    riktig_tabell = tabeller[0][0]  # Hent den første tabellen eller spesifiser en bestemt
    cursor.execute(f"SELECT * FROM {riktig_tabell}")
    rows = cursor.fetchall()

    data = b"".join([str(row).encode() for row in rows])

    cursor.close()
    conn.close()
    return data

def les_raw_database(database_path):
    with open(database_path, 'rb') as db_fil:
        data = db_fil.read()
    return data

def analyser_data(data, situasjon, csv_datasett=None):
    logging.info("Starter analyse av data for entropi og kompresjonsgrad")
    entropi = beregn_entropi(data)
    kompresjonsgrad = beregn_kompresjonsgrad(data)
    
    logging.info(f"Entropi: {entropi}")
    logging.info(f"Kompresjonsgrad: {kompresjonsgrad}")

    if csv_datasett is None:
        csv_datasett = "./../Datasett/datasett_en_med_uuids.csv"

    alle_meldinger, alle_uuider = les_meldinger_fra_csv(csv_datasett, situasjon)
    logging.debug(f"Antall meldinger: {len(alle_meldinger)}")
    logging.debug(f"Antall uuider: {len(alle_uuider)}")

    uuider = søk_etter_uuid(data, alle_uuider)
    meldinger = søk_etter_meldinger(data, alle_meldinger)
    emneknagg = søk_etter_emneknagg(data, "#NTNU-MISEB")
    kallenavn = søk_etter_kallenavn(data)
    artefakter = søk_etter_kryptografiskealgoritmer(data)
    logging.info(f"Funnet uuider: {uuider}")
    logging.info(f"Funnet meldinger: {meldinger}")
    logging.info(f"Funnet emneknagg: {emneknagg}")
    logging.info(f"Funnet kallenavn: {kallenavn}")
    logging.info(f"Funnet kryptografiske artefakter: {artefakter}")

    return entropi, kompresjonsgrad, uuider, meldinger, emneknagg, kallenavn, artefakter

def legg_til_i_resultater(resultater, database_path, db_lesbar, entropi, kompresjonsgrad, avsender, situasjon, uuid, meldinger, emneknagg, kallenavn, artefakter, tabeller):
    resultat = {
        "sit.": situasjon,
        "avsender": avsender,
        "db_lesbar": db_lesbar,
        "entropi": entropi,
        "kompresjonsgrad": kompresjonsgrad,
        "uuid": uuid,
        "meldinger": meldinger,
        "emneknagg": emneknagg,
        "kallenavn": kallenavn,
        "krypteringsartefakter": artefakter,
        "database_path": database_path,
        "tidspunkt": datetime.now().isoformat(),
        "db-tabeller": tabeller if db_lesbar else False
    }
    resultater.append(resultat)

def finn_og_analyser_filer(base_dir):
    resultater = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "db.mv.db":
                database_path = os.path.join(root, file)
                path_parts = database_path.split(os.sep)
                
                try:
                    avsender = path_parts[path_parts.index("kopier") + 1]
                    situasjon_str = path_parts[path_parts.index("kopier") + 2]

                    situasjon_match = re.search(r'situasjon_(\d+)-', situasjon_str)
                    if situasjon_match:
                        situasjon = int(situasjon_match.group(1))
                    else:
                        logging.error(f"Ugyldig format for situasjon i {database_path}")
                        continue

                except (IndexError, ValueError):
                    logging.error(f"Ugyldig mappestruktur for {database_path}")
                    continue

                tabeller = []
                db_data = les_h2_database(database_path)
                if db_data is None:
                    db_lesbar = False
                    data = les_raw_database(database_path)
                else:
                    db_lesbar = True
                    tabeller = [t[0] for t in db_data]  # Legger til tabellnavnene
                    data = db_data

                entropi, kompresjonsgrad, uuid, meldinger, emneknagg, kallenavn, artefakter = analyser_data(data, situasjon)
                legg_til_i_resultater(resultater, database_path, db_lesbar, entropi, kompresjonsgrad, avsender, situasjon, uuid, meldinger, emneknagg, kallenavn, artefakter, tabeller)

    return resultater

def skriv_samlede_resultater_til_json(resultater):
    resultater_sortert = sorted(resultater, key=lambda x: (x["sit."], x["avsender"]))

    #timestamp = datetime.now().isoformat().replace(":", "-")
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M')
    json_filnavn = f"resultat-lokallagring-samlet-{timestamp}.json"
    json_sti = os.path.join("./resultater", json_filnavn)
    os.makedirs(os.path.dirname(json_sti), exist_ok=True)

    with open(json_sti, 'w') as json_fil:
        json.dump(resultater_sortert, json_fil, indent=4)

    logging.critical(f"Samlede resultater skrevet til {json_sti}")
    print(f"Samlede resultater skrevet til {json_sti}")

def main():
    parser = argparse.ArgumentParser(description="Rekursiv analyse av H2-databasefiler.")
    parser.add_argument('-d', '--directory', default="./kopier", help="Path til rotmappen for analyse.")
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Øk verbose nivå: -v for INFO, -vv for DEBUG")
    args = parser.parse_args()

    logger = setup_logger(args.verbose)
    resultater = finn_og_analyser_filer(args.directory)
    skriv_samlede_resultater_til_json(resultater)

if __name__ == "__main__":
    main()
