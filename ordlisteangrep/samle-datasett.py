import os
import json
import logging
import argparse
from datetime import datetime
from collections import OrderedDict  # For å beholde rekkefølgen i dict

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

# Funksjon for å finne den nyeste JSON-filen basert på modifiseringsdato
def finn_nyeste_json_fil(mappe_sti):
    json_filer = [f for f in os.listdir(mappe_sti) if f.endswith('.json')]
    
    if not json_filer:
        return None
    
    # Finn filen med den nyeste modifiseringsdatoen
    nyeste_fil = max(json_filer, key=lambda f: os.path.getmtime(os.path.join(mappe_sti, f)))
    return os.path.join(mappe_sti, nyeste_fil)

# Funksjon for å lese enhetsnavn fra enheter.conf
def les_enhetsnavn(filnavn='enheter.conf'):
    with open(filnavn, 'r') as f:
        enhetsnavn = [linje.strip().strip('[]') for linje in f.read().splitlines() if linje.strip()]
    return enhetsnavn

# Funksjon for å samle data fra spesifikke enheter
def samle_data(status_katalog='./status', enheter_fil='enheter.conf'):
    samlet_data = []
    enhetsnavn_liste = les_enhetsnavn(enheter_fil)
    
    # Gå gjennom hver mappe i status-katalogen (enhetens mapper)
    for enhet_navn in enhetsnavn_liste:
        logging.debug(enhet_navn)
        enhet_mappe = os.path.join(status_katalog, enhet_navn)
        
        if os.path.isdir(enhet_mappe):  # Sørg for at vi kun ser på mapper
            nyeste_fil = finn_nyeste_json_fil(enhet_mappe)
            
            if nyeste_fil:
                # Les innholdet i den nyeste JSON-filen
                with open(nyeste_fil, 'r') as f:
                    json_data = json.load(f)
                
                # Lag en ny OrderedDict der "enhet" og "json_filnavn" legges inn først
                ordnet_data = OrderedDict()
                ordnet_data['enhet'] = enhet_navn
                ordnet_data['json_filnavn'] = os.path.basename(nyeste_fil)

                # Legg til de opprinnelige dataene etterpå
                ordnet_data.update(json_data)
                samlet_data.append(ordnet_data)
    
    return samlet_data

# Funksjon for å lagre det samlede datasettet til en ny JSON-fil
def lagre_datasett_til_fil(data, utdata_katalog='./resultater'):
    os.makedirs(utdata_katalog, exist_ok=True)
    
    # Lag ISO-tidsstempel for filnavn
    tidsstempel = datetime.now().isoformat(timespec='seconds').replace(':', '-')
    utdata_fil = os.path.join(utdata_katalog, f"{tidsstempel}-datasett.json")
    
    # Lagre data som JSON-fil
    with open(utdata_fil, 'w') as f:
        json.dump(data, f, indent=4)
    
    logging.info(f"Datasettet er lagret til {utdata_fil}")

# Hovedfunksjon for å samle og lagre datasettet
def main(inndata_katalog='./status', utdata_katalog='./resultater', enheter_fil=None):
    log_path = sett_opp_logging()
    logging.info(f"Loggfil opprettet: {log_path}")
    
    logging.info("Starter datainnsamling...")
    samlet_data = samle_data(inndata_katalog, enheter_fil)
    
    if not samlet_data:
        logging.warning("Ingen data funnet.")
        return
    
    lagre_datasett_til_fil(samlet_data, utdata_katalog)
    logging.info("Datainnsamling fullført.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Samle og lagre datasett fra enheter.")
    parser.add_argument('--inndata_katalog', type=str, default='./status', help='Katalog for statusfiler')
    parser.add_argument('--utdata_katalog', type=str, default='./resultater', help='Katalog for utdatafiler')
    parser.add_argument('--enheter_fil', type=str, default='../ressurser/enheter.conf', help='Fil med liste over enheter')
    args = parser.parse_args()
    
    main(args.inndata_katalog, args.utdata_katalog, args.enheter_fil)
