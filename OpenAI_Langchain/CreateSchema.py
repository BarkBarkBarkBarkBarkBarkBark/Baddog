# initialize.py

import csv
from collections import defaultdict

# Define a mapping from Python data types to Weaviate data types
type_mapping = {
    'str': 'DataType.TEXT',
    'int': 'DataType.INT',
    'float': 'DataType.NUMBER',
    'bool': 'DataType.BOOLEAN',
    'date': 'DataType.DATE',  # You can enhance date detection if needed
}

def infer_data_type(values):
    """Infer the data type of a list of values."""
    data_types = set()
    for value in values:
        value = value.strip()
        if value == '':
            continue  # Skip empty values
        try:
            int(value)
            data_types.add('int')
            continue
        except ValueError:
            pass
        try:
            float(value)
            data_types.add('float')
            continue
        except ValueError:
            pass
        if value.lower() in ('true', 'false'):
            data_types.add('bool')
            continue
        # Add more sophisticated checks for dates if necessary
        data_types.add('str')
    # Decide the most suitable data type
    if len(data_types) == 1:
        return data_types.pop()
    elif 'str' in data_types:
        return 'str'
    elif 'float' in data_types:
        return 'float'
    elif 'int' in data_types:
        return 'int'
    else:
        return 'str'

def generate_schema(csv_filename, schema_filename):
    with open(csv_filename, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)
        columns = defaultdict(list)
        for row in reader:
            for i, value in enumerate(row):
                # Handle missing columns in rows
                if i < len(headers):
                    columns[headers[i]].append(value)
        properties = []
        for header in headers:
            values = columns[header]
            data_type = infer_data_type(values)
            weaviate_data_type = type_mapping.get(data_type, 'DataType.TEXT')
            properties.append({
                'name': header,
                'data_type': weaviate_data_type,
                'vectorize_property_name': True,
                'skip_vectorization': True,
            })
    # Generate the schema.py file
    with open(schema_filename, 'w') as file:
        for prop in properties:
            # Include the arbitrary attributes
            line = (
                f'Property(name="{prop["name"]}", data_type={prop["data_type"]}, '
                f'vectorize_property_name={prop["vectorize_property_name"]}, '
                f'skip_vectorization={prop["skip_vectorization"]})\n'
            )
            file.write(line)
    print(f"File '{schema_filename}' has been created with the inferred properties.")

if __name__ == "__main__":
    # Request the CSV file path and output schema file name from the user
    csv_filename = input("Enter the full path of the CSV file: ").strip()
    schema_filename = input("Enter the output schema file name (e.g., schema.py): ").strip()
    generate_schema(csv_filename, schema_filename)
