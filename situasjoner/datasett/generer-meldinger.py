import os
import csv
import argparse

def create_files_from_csv(file_path):
    if "datasett_en" in file_path:
        dest_path = 'meldinger/en'
    elif "datasett_no" in file_path:
        dest_path = 'meldinger/no'
    else:
        raise ValueError("CSV-filen må inneholde enten 'datasett_en' for engelsk eller 'datasett_no' for norsk i filnavnet.")
    
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        
        # Sjekk at kolonnenavn inneholder 'Melding'
        if 'Melding' not in reader.fieldnames:
            raise ValueError("CSV-filen må inneholde en kolonne kalt 'Melding'")
        
        for row in reader:
            filename = f"{row['Situasjon']}_{row['Kanal']}_{row['MeldingsNummer']}_{row['Avsender']}_{row['Mottaker']}.txt"

            message_content = row['Melding']
            
            filepath = os.path.join(dest_path, filename)
            
            with open(filepath, mode='w', encoding='utf-8') as outfile:
                outfile.write(message_content)
                
            print(f"Laget fil: {filepath}")

def parse_arguments():
    """
    Parser kommandolinjeargumenter for å få CSV-filens sti.
    Returnerer stien til CSV-filen eller standard hvis ingen er angitt.
    """
    parser = argparse.ArgumentParser(description='Generer filer basert på meldinger i en CSV-fil.')
    parser.add_argument(
        '--csv-file',
        type=str, default='datasett_en_med_uuids.csv',
        help='Stien til CSV-filen (standard er datasett_en_med_uuids.csv)'
    )
    args = parser.parse_args()
    
    return args.csv_file

def main():
    csv_file_path = parse_arguments()
    
    create_files_from_csv(csv_file_path)

if __name__ == "__main__":
    main()
