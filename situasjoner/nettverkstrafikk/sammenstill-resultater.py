import os
import json
import csv
import argparse
import logging
from datetime import datetime

def setup_logging(timestamp):
    # Opprett loggmappen hvis den ikke eksisterer
    log_dir = './log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    

    script_navn = os.path.splitext(os.path.basename(__file__))[0]  # Hent navnet på scriptet uten filendelsen
    log_filnavn = f'{script_navn}-{timestamp}.log'
    log_filepath = os.path.join('./log', log_filnavn)


    # Konfigurer logging
    logging.basicConfig(
        filename=log_filepath,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )
    
    logging.info('Startet sammenstilling av JSON-filer')

def find_latest_subfolder(base_path):
    # Finn nyeste undermappe i base_path
    subfolders = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    if not subfolders:
        return None
    latest_subfolder = max(subfolders, key=os.path.getmtime)
    return latest_subfolder

def merge_json_files(base_path):
    merged_data = []
    
    # Gå gjennom situasjonene fra 1 til 7
    for situasjon in range(1, 8):
        situasjon_path = os.path.join(base_path, f'situasjon_{situasjon}')
        if not os.path.exists(situasjon_path):
            logging.warning(f'Mappen for situasjon {situasjon} eksisterer ikke: {situasjon_path}')
            continue
        
        # Finn nyeste undermappe i situasjonens mappe
        latest_folder = find_latest_subfolder(situasjon_path)
        if latest_folder is None:
            logging.warning(f'Fant ingen undermapper for situasjon {situasjon}')
            continue
        
        # Finn JSON-filen i den nyeste undermappen
        json_files = [f for f in os.listdir(latest_folder) if f.endswith('.json')]
        if not json_files:
            logging.warning(f'Ingen JSON-filer funnet i {latest_folder}')
            continue
        
        json_file_path = os.path.join(latest_folder, json_files[0])
        
        # Les JSON-filen
        try:
            with open(json_file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                merged_data.append(data)
                logging.info(f'Suksessfullt lastet JSON-fil fra {json_file_path}')
        except Exception as e:
            logging.error(f'Feil ved lesing av {json_file_path}: {str(e)}')
    
    return merged_data

def save_merged_data(merged_data, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        logging.info(f'Sammenstilte data lagret i {output_file}')
    except Exception as e:
        logging.error(f'Feil ved lagring av sammenstilte data: {str(e)}')

def extract_relevant_data(merged_data):
    relevant_data = []
    
    for situasjon_data in merged_data:
        situasjonsnummer = situasjon_data.get('situasjonsnummer', 'Ukjent situasjon')

        # Iterer over avsendere
        for avsender in situasjon_data.get('avsendere', []):
            avsendernavn = avsender.get('navn', 'Ukjent avsender')

            # Iterer over kanaler for hver avsender
            for kanal in avsender.get('kanaler', []):
                kanalnavn = kanal.get('navn', 'Ukjent kanal')
                entropi = kanal.get('entropi', 'Ukjent entropi')
                komprimeringsgrad = kanal.get('kompresjonsrate', 'Ukjent komprimeringsgrad')
                hele_meldinger = kanal.get('funnet_hele_meldinger', [])
                uuid = kanal.get('funnet_uuid', [])
                emneknagg = kanal.get('funnet_emneknagg', [])
                kallenavn = kanal.get('funnet_kallenavn', [])
                kryptografiske_artefakter = kanal.get('funnet_kryptografiske_artefakter', [])

                # Legg til relevant informasjon i listen
                relevant_data.append({
                    'situasjon': situasjonsnummer,
                    'avsendernavn': avsendernavn,
                    'kanalnavn': kanalnavn,
                    'entropi': entropi,
                    'komprimeringsgrad': komprimeringsgrad,
                    'hele_meldinger': hele_meldinger,
                    'uuid': uuid,
                    'emneknagg': emneknagg,
                    'kallenavn': kallenavn,
                    'kryptografiske_artefakter': kryptografiske_artefakter
                })
    
    return relevant_data

def save_to_csv(relevant_data, output_file):
    felter_dict = {
        "beregning": {
            "felter": ['situasjon', 'avsendernavn', 'kanalnavn', 'entropi', 'komprimeringsgrad']
        },
        "klartest": {
            "felter": ['situasjon', 'avsendernavn', 'kanalnavn', 'hele_meldinger', 'uuid', 'emneknagg', 'kallenavn']
        },
        "artefakter": {
            "felter": ['situasjon', 'avsendernavn', 'kanalnavn', 'kryptografiske_artefakter']
        }
    }

    for kategori, innhold in felter_dict.items():
        filnavn = output_file + f"_{kategori}.csv"  # Bruker et nytt filnavn for hver kategori
        try:
            with open(filnavn, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=innhold['felter'], delimiter=';')
                writer.writeheader()
                
                for row in relevant_data:
                    relevant_row = {key: row.get(key, '') for key in innhold['felter']}
                    writer.writerow(relevant_row)

            
            logging.info(f'Relevante data lagret i CSV-fil: {filnavn}')
        except Exception as e:
            logging.error(f'Feil ved lagring av CSV-fil: {str(e)}')
    

def main():
    # Sett opp argumenter
    parser = argparse.ArgumentParser(description='Sammenstilling av JSON-filer fra situasjonsmapper.')
    parser.add_argument('--path', type=str, default='./situasjons_pakkedumper/', help='Sti til situasjonsmapper')
    
    args = parser.parse_args()
    
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')

    # Sett opp logging
    setup_logging(timestamp)

    # Slå sammen JSON-filene
    merged_data = merge_json_files(args.path)
    
    if merged_data:
        # Lagre den sammenstilte JSON-filen
        output_file = os.path.join(args.path, f'{timestamp}-sammenstilte-resultater.json')
        save_merged_data(merged_data, output_file)
        
        # Ekstraher og lagre relevante data til CSV-fil
        relevant_data = extract_relevant_data(merged_data)
        if relevant_data:
            output_csv = os.path.join(args.path, f'{timestamp}-relevante-resultater')
            save_to_csv(relevant_data, output_csv)
        else:
            logging.warning('Ingen relevante data funnet å lagre i CSV')
    else:
        logging.warning('Ingen data å slå sammen')

if __name__ == '__main__':
    main()
