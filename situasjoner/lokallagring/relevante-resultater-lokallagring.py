import argparse
import logging
import json
import os
import csv
from datetime import datetime
import re

def sett_opp_logging():
    """
    Setter opp dynamisk log-filnavn basert på scriptets navn og nåværende timestamp.
    """
    script_navn = os.path.splitext(os.path.basename(__file__))[0]
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    log_filnavn = f'{script_navn}-{timestamp}.log'
    log_path = os.path.join('./log', log_filnavn)
    os.makedirs('./log', exist_ok=True)
    logging.basicConfig(filename=log_path, level=logging.INFO, 
                        format='%(asctime)s %(levelname)s:%(message)s')
    return log_path

def finn_nyeste_json(resultat_dir='./resultater/'):
    """
    Finner den nyeste JSON-filen i resultatkatalogen.
    
    Args:
        resultat_dir (str): Katalogen der resultatfilene ligger.
    
    Returns:
        str: Stien til den nyeste JSON-filen.
    
    Raises:
        FileNotFoundError: Hvis ingen JSON-filer finnes i katalogen.
    """
    json_filer = [f for f in os.listdir(resultat_dir) if f.endswith('.json')]
    if not json_filer:
        raise FileNotFoundError("Ingen JSON-filer funnet i resultat-mappen.")
    nyeste_fil = max(json_filer, key=lambda f: os.path.getmtime(os.path.join(resultat_dir, f)))
    return os.path.join(resultat_dir, nyeste_fil)


def hent_resultater(json_path):
    """
    Henter resultater fra en JSON-fil.
    
    Args:
        json_path (str): Stien til JSON-filen.
    
    Returns:
        list: En liste over resultater.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Hvis data er et enkelt objekt, pakk det inn i en liste
    if isinstance(data, dict):
        data = [data]
    
    return data



def skriv_til_csv(data, json_path):
    """
    Skriver data til en CSV-fil.
    
    Args:
        data (list): En liste over data som skal skrives til CSV.
        json_path (str): Stien til JSON-filen for å generere CSV-filnavnet.
    """
    
    # Definer de relevante feltene og deres rekkefølge

    felter_dict = {
        "alle": {
            "felter": ['database_path', 'db_lesbar', 'entropi', 'kompresjonsgrad', 'avsender', 'sit.', 'uuid', 'meldinger', 'emneknagg', 'kallenavn', 'krypteringsartefakter', 'tidspunkt']
        },
        "database": {
            "felter": ['sit.', 'avsender', 'db_lesbar', 'db-tabeller']
        },
        "beregning": {
            "felter": ['sit.', 'avsender', 'entropi', 'kompresjonsgrad']
        },
        "klartekst": {
            "felter": ['sit.', 'avsender', 'uuid', 'meldinger', 'emneknagg', 'kallenavn']
        },
        "artefakter": {
            "felter": ['sit.', 'avsender', 'krypteringsartefakter']
        }
    }


    for kategori, innhold in felter_dict.items():
        csv_filnavn = os.path.splitext(os.path.basename(json_path))[0] + f"_{kategori}.csv"
        output_fil = os.path.join(os.path.dirname(json_path), csv_filnavn)

        with open(output_fil, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=innhold['felter'], delimiter=';')
            
            writer.writeheader()
            for row in data:
                relevant_row = {key: row.get(key, '') for key in innhold['felter']}
                writer.writerow(relevant_row)
        
        logging.info(f"Data skrevet til CSV-fil: {output_fil}")

def main(resultat_dir):
    """
    Hovedfunksjon for å hente relevante resultater og skrive dem til en CSV-fil.
    
    Args:
        resultat_dir (str): Katalogen der resultatfilene ligger.
    """
    log_path = sett_opp_logging()
    logging.info(f"Loggfil opprettet: {log_path}")
    
    try:
        nyeste_json = finn_nyeste_json(resultat_dir)
        logging.info(f"Fant nyeste JSON-fil: {nyeste_json}")
        
        relevante_resultater = hent_resultater(nyeste_json)
        if relevante_resultater:
            skriv_til_csv(relevante_resultater, nyeste_json)
        else:
            logging.warning("Ingen relevante resultater å skrive til CSV.")
    except Exception as e:
        logging.error(f"En feil oppstod: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hent relevante resultater fra JSON og skriv til CSV.")
    parser.add_argument('--resultat_dir', type=str, default='./resultater', help='Katalogen der resultatfilene ligger')
    args = parser.parse_args()
    
    main(args.resultat_dir)
