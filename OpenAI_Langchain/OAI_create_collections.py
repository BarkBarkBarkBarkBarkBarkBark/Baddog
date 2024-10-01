import weaviate
import pandas as pd
import math

# Definizione variabile percorso csv
csv_file = "/Users/marco/Desktop/HealthScout/HealthScoutDatabase.csv"
client = weaviate.connect_to_local(skip_init_checks=True)

# Impostazioni per monitorare il progresso dell'importazione
counter = 0
interval = 100  # stampa il progresso ogni questo numero di record
batch_size = 200  # imposta la dimensione del batch

# Funzione per gestire l'importazione dei dati
def add_object_to_collections(row) -> None:
    global counter

    # Sostituisci i valori NaN con stringhe vuote
    row = row.fillna("")

    # Inserimento oggetto nella proprietà geo_location con riferimenti
    try:
        latitude = float(row["Latitude"])
        longitude = float(row["Longitude"])
    except ValueError:
        # Se latitudine o longitudine non sono validi, usa valori predefiniti (es: 0.0)
        latitude = 0.0
        longitude = 0.0

    # Inserimento oggetti nella collezione 'sacramento'
    sacramento_properties = {
        "first_name": row["Provider First Name"],
        "last_name": row["Provider Last Name"],
        "doc_phone": str(row["Telephone Number"]),
        "doc_title": row["Cred"],
        "specialization": row["pri_spec"],
        "doc_address": row["adr_ln_1"],
        "geo_location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "insurance_name": row["Managed Care Plan"],
        "facility_name": row["Facility Name"],
        "city": row["City/Town"],
        "transportation_name": row["Transportation Provider"],
        "transportation_phone": str(row["Phone Number for Transportation"]),
        "transportation_desc": row["Benefit Description"],
        "search_tags": row["terms"]
    }
    insurance_uuid = client.collections.get("sacramento").data.insert(properties=sacramento_properties)

    # Calcolo e visualizzazione del progresso
    counter += 1
    if counter % interval == 0:
        print(f"Imported {counter} records...")

# Importazione dei dati tramite lazy loading e batching
print("Importazione dei dati tramite streaming con pandas...")

with pd.read_csv(
    csv_file,
    chunksize=100  # numero di righe per ogni chunk
) as csv_iterator:
    with client.batch.fixed_size(batch_size=batch_size) as batch:
        for chunk in csv_iterator:
            for _, row in chunk.iterrows():
                add_object_to_collections(row)

client.close()

print(f"Importazione completata con successo! Totale record importati: {counter}")

