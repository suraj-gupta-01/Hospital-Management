import os
from flask import Flask, request, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Supabase Configuration
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def extract_fhir_data(bundle_json):
    """
    Parses a FHIR Bundle to extract specific medical information.
    """
    extracted = {
        "diagnosis": "Not Specified",
        "medications": [],
        "lab_results": [],
        "visit_date": None
    }
    
    # Loop through all resources in the bundle
    for entry in bundle_json.get("entry", []):
        resource = entry.get("resource", {})
        r_type = resource.get("resourceType")
        
        # 1. Extract Diagnosis (Condition)
        if r_type == "Condition":
            extracted["diagnosis"] = resource.get("code", {}).get("text", "Unknown")
            
        # 2. Extract Medications
        elif r_type == "MedicationRequest":
            med_name = resource.get("medicationCodeableConcept", {}).get("text")
            dosage = resource.get("dosageInstruction", [{}])[0].get("text", "As directed")
            extracted["medications"].append({"name": med_name, "dosage": dosage})
            extracted["visit_date"] = resource.get("authoredOn")

        
        # # 3. Extract Lab Results (Observations) - ADDED FOR FUTURE USE
        # elif r_type == "Observation":
        #     test_name = resource.get("code", {}).get("text", "Unknown Test")
            
        #     # Observations can have different value types; quantity is most common
        #     value_quantity = resource.get("valueQuantity", {})
        #     value = value_quantity.get("value")
        #     unit = value_quantity.get("unit", "")
            
        #     # Create a readable string like "Blood Glucose: 110 mg/dL"
        #     result_string = f"{test_name}: {value} {unit}".strip()
            
        #     # You might want a new list in your 'extracted' dict for this:
        #     if "lab_results" not in extracted:
        #         extracted["lab_results"] = []
        #     extracted["lab_results"].append(result_string)

    return extracted

@app.route('/extract-and-store', methods=['POST'])
def handle_medical_record():
    try:
        # 1. Get the raw FHIR JSON from the request
        raw_data = request.json
        if not raw_data:
            return jsonify({"error": "No data provided"}), 400

        # 2. Run the Parser
        data_to_save = extract_fhir_data(raw_data)
        
        # 3. Add metadata (e.g., ABHA Address from headers or request)
        abha_address = request.args.get('abha_address') # e.g., name@abdm
        
        # 4. Insert into Supabase
        result = supabase.table("medical_records").insert({
            "abha_address": abha_address,
            "diagnosis": data_to_save["diagnosis"],
            "medications": data_to_save["medications"], # Saved as JSONB
            "visit_date": data_to_save["visit_date"],
            "raw_fhir_json": raw_data # Store original for reference
        }).execute()

        return jsonify({"status": "success", "data_stored": data_to_save}), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)