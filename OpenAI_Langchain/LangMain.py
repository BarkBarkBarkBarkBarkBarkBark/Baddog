import os
from dotenv import load_dotenv
import openai
from weaviate import Client
from langchain.prompts import PromptTemplate

import warnings
import logging

warnings.filterwarnings("ignore", category=DeprecationWarning)

logging.getLogger("dotenv").setLevel(logging.ERROR)

# Load environment variables from the .env file
load_dotenv()

# Set up your OpenAI API key
openai.api_key=os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

# Prepare the prompt template for query
template_user="""
You will be provided with a query related to healthcare assistance and insurance.
Your task is to summarize and split the query into three sections:

**Ensure that your response strictly follows this format:**

Here are the results:

* **assistance:** The part of the query describing the medical assistance needed.
* **insurance:** The name of the insurance provider mentioned in the query.
* **specialty:** The medical specialty that is most relevant to the assistance needed.

ONLY provide the 'assistance', 'insurance', and 'specialty' without any parentheses or commas.
If the 'insurance' is molina or molina healthcare, your format will be molina_healthcare.
If the 'insurance' is blue cross or blue shield or blue cross blue shield, your format will be blue_cross_blue_shield.
If the 'insurance' is anthem or blue anthem or anthem blue cross blue shield, your format will be anthem_blue_cross_blue_shield.
If no insurance provider is mentioned, leave the 'insurance' section empty.

**In determining the 'specialty', prioritize the following:**

1. **Explicit mentions of medical professionals or specialties:** If the query directly states the type of doctor or medical field needed (e.g., "cardiologist", "dermatology"), use that as the 'specialty'.
2. **Procedures or treatments:** If the query mentions specific procedures or treatments, infer the most likely specialty associated with them (e.g., "root canal" -> "dentist", "mammogram" -> "radiologist").
3. **Symptoms or conditions:** If the query describes symptoms or conditions, deduce the most relevant specialty that typically handles such cases (e.g., "chest pain" -> "cardiologist", "rash" -> "dermatologist").

**Query:** {query}

**assistance:** 
**insurance:** 
**specialty:** 
"""

# Use the Template as the actual prompt
prompt_user = PromptTemplate(template=template_user, input_variables=["query"])

# Connect to Weaviate (initialize once)
client = Client(
    url="http://localhost:8080",
    additional_headers={
        "X-OpenAI-Api-Key": openai.api_key  # Include if using generative modules
    }
)

# Define a function to format doctor info (outside the loop)
def format_doctor_info(doctor):
    first_name = doctor.get('first_name', '')
    last_name = doctor.get('last_name', '')
    specialization = doctor.get('specialization', '')
    insurance_name = doctor.get('insurance_name', '')
    city = doctor.get('city', '')
    transportation_name = doctor.get('transportation_name', '')
    transportation_phone = doctor.get('transportation_phone', '')
    transportation_desc = doctor.get('transportation_desc', '')

    doctor_info = f"""
- Doctor: {first_name} {last_name}
- Specialization: {specialization}
- Insurance: {insurance_name}
- City: {city}
- Transportation:
    - Provider: {transportation_name}
    - Phone: {transportation_phone}
    - Information: {transportation_desc}
"""
    return doctor_info

# Start the loop
while True:
    # User Query via terminal
    query_user = input("Please write your question here (or type 'exit' to quit): ")
    if query_user.lower() in ['exit', 'quit']:
        print("Goodbye!")
        break

    # Format the prompt
    formatted_prompt = prompt_user.format(query=query_user)

    # Prepare the OpenAI API call
    response = openai.ChatCompletion.create(
        model="gpt-4",  # You can switch to "gpt-3.5-turbo" for lower cost
        messages=[
            {"role": "system", "content": "You are a helpful assistant that processes healthcare queries."},
            {"role": "user", "content": formatted_prompt}
        ],
        temperature=0  # For deterministic output
    )

    # Extract the generated response
    output_user = response['choices'][0]['message']['content']

    # Print Output for debugging
    print("\nOutput from OpenAI:\n", output_user)

    # Splitting lines
    lines = output_user.strip().split("\n")

    # Create a dictionary for storing data
    data = {}

    # Run a for loop over the lines and extract information
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().replace("*", "").strip().lower()
            value = value.strip().replace("*", "").strip()
            data[key] = value

    # Create variables and assign data
    assistance = data.get("assistance", "")
    insurance = data.get("insurance", "")
    specialty = data.get("specialty", "")

    # Print Vars
    print("\nExtracted Information:")
    print("Var Assistance:", assistance)
    print("Var Insurance:", insurance)
    print("Var Specialty:", specialty)

    # Build the where filter dynamically
    filters = []

    if insurance:
        filters.append({
            "path": ["insurance_name"],
            "operator": "Equal",
            "valueText": insurance
        })

    if specialty:
        filters.append({
            "path": ["specialization"],
            "operator": "Equal",
            "valueText": specialty
        })

    if filters:
        if len(filters) == 1:
            where_filter = filters[0]
        else:
            where_filter = {
                "operator": "And",
                "operands": filters
            }
    else:
        where_filter = None  # No filters

    # Build the query
    query = client.query.get(
        "sacramento",  # Replace with your actual class name
        [
            "first_name",
            "last_name",
            "specialization",
            "insurance_name",
            "city",
            "transportation_name",
            "transportation_phone",
            "transportation_desc",
        ]
    )

    if where_filter:
        query = query.with_where(where_filter)

    # Set limit of results
    query = query.with_limit(3)

    # Execute the query
    response_weaviate = query.do()

    # Check if data is in the response
    if 'data' in response_weaviate and 'Get' in response_weaviate['data'] and 'sacramento' in response_weaviate['data']['Get']:
        results = response_weaviate['data']['Get']['sacramento']
    else:
        results = []

    # Print the results for debugging
    print("\nWeaviate Results:", results)

    if results:
        doctor_infos = [format_doctor_info(doctor) for doctor in results]
        doctors_info_str = "\n".join(doctor_infos)
    else:
        doctors_info_str = "I'm sorry, but I couldn't find any doctors matching your criteria."

    # Construct the final prompt
    final_prompt = f"""
Based on your request for assistance: "{assistance}", insurance: "{insurance}", and specialty: "{specialty}", here are some doctors that might be able to help:

{doctors_info_str}

Please let me know if you need further assistance or information.
"""

    # Now, use OpenAI's API to generate a natural language response
    response_final = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system",
             "content":  """
You are a chatbot assistant that ONLY provides the doctors who accept the provided insurance.
Provide ONLY the doctors that are specialized in the provided specialty. If not sure, you can check search tags for more info.

Respond ONLY with the following data in this EXACT format, DO NOT truncate the data, and provide the data every time:

- Doctor: {first_name} {last_name}
- Specialization: {specialization}
- Insurance: {insurance_name}
- City: {city}
- Transportation:
    - Provider: {transportation_name}
    - Phone: {transportation_phone}
    - Information: {transportation_desc}

DO NOT provide any additional information or context.
DO NOT act as the doctor.
DO NOT provide medical advice.
Please provide three responses.
"""
             },
            {"role": "user", "content": final_prompt}
        ],
        temperature=0.7
    )

    # Extract the assistant's reply
    assistant_reply = response_final['choices'][0]['message']['content']

    # Print the assistant's reply
    print("\nAssistant's Response:\n", assistant_reply)

# No need to close the client connection
