# hjelpefunksjoner.py
import math
import zlib
import csv

# Felles hjelpefunksjon for beregning av entropi
def beregn_entropi(data):
    if len(data) == 0:
        return 0
    frekvenser = {}
    for byte in data:
        frekvenser[byte] = frekvenser.get(byte, 0) + 1

    entropi = 0
    for freq in frekvenser.values():
        p = freq / len(data)
        entropi -= p * math.log2(p)

    return round(entropi, 2)


def beregn_entropi_original_datasett(data):
    if len(data) == 0:
        return 0

    frekvenser = {}
    
    # Itererer gjennom hver melding og hvert tegn i meldingen
    for melding in data:
        for byte in melding:
            frekvenser[byte] = frekvenser.get(byte, 0) + 1

    entropi = 0
    total_tegn = sum(frekvenser.values())  # Totalt antall tegn
    
    # Beregn entropi basert på tegnfrekvenser
    for freq in frekvenser.values():
        p = freq / total_tegn
        entropi -= p * math.log2(p)

    return round(entropi, 2)



# Felles hjelpefunksjon for beregning av kompresjonsgrad
def beregn_kompresjonsgrad(data):
    if len(data) == 0:
        return 0.0
    compressed_data = zlib.compress(data)
    kompresjonsgrad = len(compressed_data) / len(data)
    return round(kompresjonsgrad, 2)


def søk_etter_uuid(samlet_payload, uuider):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_uuid = []

    for uuid_nummer, uuid in enumerate(uuider, start=1):
        #logger.debug(f"Søker etter uuid {uuid_nummer}: {uuid}")
        if uuid in samlet_payload_str:
            funnet_uuid.append(uuid)
            #logger.warning(f"Funnet uuid {uuid_nummer}: {uuid}")

    if not funnet_uuid:
        #logger.info(f"Ingen UUID-er funnet.")
        return False
    
    return funnet_uuid


def søk_etter_emneknagg(samlet_payload, emneknagg):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_emneknagg = False

    #self.logger.debug(f"Søker etter emneknagg: {emneknagg} i samlet_payload_str:\n{samlet_payload_str}")
    if emneknagg in samlet_payload_str:
        funnet_emneknagg = True
        #self.logger.warning(f"Funnet emneknagg {emneknagg} i samlet_payload_str!!!")

    if not funnet_emneknagg:
        #self.logger.info(f"Ingen emneknagg funnet i {self.navn}.")
        return False
    
    return funnet_emneknagg


# Funksjon for å søke etter meldinger i pakkedumpene
def søk_etter_kallenavn(samlet_payload):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_kallenavn = []
    avsendere = ['Alice', 'Bob', 'Charlie', 'Dave']

    for kallenavn in avsendere:
        kallenavn_str = kallenavn
        #self.logger.debug(f"Søker etter kallenavn: {kallenavn_str} i samlet_payload_str")

        if kallenavn_str in samlet_payload_str:
            funnet_kallenavn.append(kallenavn_str)
            #self.logger.warning(f"Funnet kallenavn: {kallenavn_str} i samlet_payload_str!!!")

    if not funnet_kallenavn:
        #self.logger.info(f"Ingen kallenavn funnet i {self.navn}.")
        return False
    
    return funnet_kallenavn


# Funksjon for å søke etter kjente kryptografiske_artefakter i samlet_payload
def søk_etter_kryptografiskealgoritmer(samlet_payload):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_kryptografiske_artefakter = []
    kryptografiske_algoritmer = ['AES', 'EC25519', 'ECDH', 'HMAC', 'SHA256', 'ED25519', 'X25519', 'H2', 'ECDSA', 'H2encrypt'] # test
    kryptografiske_nøkkelord = ['encrypt', 'decrypt', 'sign', 'verify', 'key exchange', 'hash', 'cipher', 'salt', 'nonce', 'IV', 'symmetric', 'asymmetric', 'public key', 'private key', 'encrypted'] # test
    tor_nøkkelord = ['onion']

    kombinertliste = kryptografiske_algoritmer + kryptografiske_nøkkelord + tor_nøkkelord

    for algoritme in kombinertliste:
        #self.logger.debug(f"Søker etter kryptografiske artefakter: {algoritme}")

        if algoritme in samlet_payload_str:
            funnet_kryptografiske_artefakter.append(algoritme)
            #self.logger.warning(f"{self.navn}: Funnet kryptografiske artefakt: {algoritme}")

    if not funnet_kryptografiske_artefakter:
        #self.logger.info(f"Ingen kryptografiske artefakter funnet i {self.navn}.")
        return False
    
    return funnet_kryptografiske_artefakter

# Funksjon for å søke etter meldinger i pakkedumpene
def søk_etter_meldinger(samlet_payload,  meldinger):
    samlet_payload_str = samlet_payload.decode('utf-8', errors='ignore')
    funnet_hele_meldinger = []


    for melding_nummer, melding in enumerate(meldinger, start=1):
        #self.logger.debug(f"Søker etter melding {melding_nummer}: {melding}")
        if melding in samlet_payload_str:
            funnet_hele_meldinger.append(melding)
            #self.logger.warning(f"Funnet melding {melding_nummer}: {melding}")

    if not funnet_hele_meldinger:
        #self.logger.info(f"Ingen hele meldinger funnet i {self.navn}.")
        return False
    
    return funnet_hele_meldinger




# Felles hjelpefunksjon for å lese relevante meldinger fra datasett
def les_meldinger_fra_csv(csv_fil, situasjonsnummer):
    meldinger = []
    uuider = []
    try:
        with open(csv_fil, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row_num, row in enumerate(reader, start=1):
                # Filtrer meldinger basert på "Situasjon" som matcher situasjonsnummeret
                if int(row['Situasjon']) == situasjonsnummer:
                    meldinger.append(row['Melding'])
                    #self.logger.debug(f"Situasjon {self.situasjonsnummer}, Melding {(row_num - 1) % 50 + 1}: {row['Melding']}")
                    
                    uuider.append(row['UUID'])
                    #self.logger.debug(f"Situasjon {self.situasjonsnummer}, Melding {(row_num - 1) % 50 + 1}: {row['UUID']}")
    except FileNotFoundError:
        pass
        #self.logger.warning(f"CSV-fil ikke funnet: {self.csv_fil}")
    except KeyError:
        pass
        #self.logger.warning(f"Kolonnen 'Melding' eller 'Situasjon' mangler i CSV-filen.")
    return meldinger, uuider