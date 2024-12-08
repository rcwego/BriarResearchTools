import uuid
import csv
import argparse
import os

def generate_uuids(n):
    """Generer n antall UUID-er og returner dem som en liste."""
    return [str(uuid.uuid4()) for _ in range(n)]

def add_uuid_column_to_csv(input_csv, output_csv):
    """Les inn CSV-filen, legg til en UUID-kolonne og skriv til en ny CSV-fil."""

    tag = "#NTNU-MISEB"

    with open(input_csv, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile, delimiter=';')
        rows = list(reader)

    header = rows[0]
    try:
        melding_index = header.index("Melding")
    except ValueError:
        print("Kolonnen 'Melding' ble ikke funnet i CSV-filen.")
        return

    uuid_list = generate_uuids(len(rows) - 1)

    updated_rows = [header + ['UUID']]
    for row, uuid_value in zip(rows[1:], uuid_list):
        if len(row) > melding_index:
            row[melding_index] += f" {tag} {uuid_value}"

        row_with_uuid = row + [uuid_value]
        updated_rows.append(row_with_uuid)

    with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter=';')
        writer.writerows(updated_rows)

    print(f"UUID-er lagt til og filen er lagret som: {output_csv}")

def parse_arguments():
    """Parser kommandolinjeargumenter og setter standardverdier."""
    parser = argparse.ArgumentParser(description='Legg til UUID-er til CSV-filer.')
    
    # Input og output filer med standardverdier
    parser.add_argument(
        '--input-csv', 
        type=str, 
        default='datasett_en.csv', 
        help='Input CSV-fil (standard: datasett.csv)'
    )
    parser.add_argument(
        '--output-csv', 
        type=str, 
        help='Output CSV-fil (standard: inputnavn_med_uuids.csv)'
    )

    # Parse argumentene
    args = parser.parse_args()

    # Sett default output-filnavn basert på input-filnavn hvis output ikke er spesifisert
    if args.output_csv is None:
        input_filename = os.path.splitext(args.input_csv)[0]  # Fjern filtypen fra input-navn
        args.output_csv = f"{input_filename}_med_uuids.csv"

    return args

def main():
    """Hovedfunksjonen for skriptet."""
    args = parse_arguments()
    
    add_uuid_column_to_csv(args.input_csv, args.output_csv)

if __name__ == "__main__":
    main()
