import json
import os
from transformers import pipeline

def extract_with_biobert(segments):
    """
    Uses a pre-trained BioBERT model to identify medical entities 
    and maps them to SOAP categories.
    """
    # Load the biomedical NER pipeline
    # This model is specifically fine-tuned for medical entity recognition
    medical_ner = pipeline("ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple")

    entities = {
        "Subjective": [], 
        "Objective": [],    
        "Assessment": [],   
        "Plan": []          
    }

    for seg in segments:
        text = seg["text"]
        speaker = seg.get("speaker", "Unknown")
        
        # Run BioBERT model on the text
        results = medical_ner(text)
        
        for entity in results:
            label = entity['entity_group'] # Entity types like 'Sign_symptom', 'Medication'
            word = entity['word']
            
            # Map BioBERT entities to SOAP sections based on clinical standards
            if label in ['Sign_symptom', 'Disease_disorder']:
                entities["Subjective"].append(f"{word} (Context: {text})")
            
            elif label in ['Diagnostic_procedure', 'Lab_value', 'Biological_structure']:
                entities["Objective"].append(f"{word} (Context: {text})")
            
            elif label in ['Medication', 'Dosage']:
                entities["Plan"].append(f"{word} (Context: {text})")

    # Basic Assessment logic for the prototype
    if entities["Subjective"] or entities["Objective"]:
        entities["Assessment"].append("Preliminary evaluation based on reported symptoms and vitals.")

    return entities

def main():
    # Corrected paths to work when running from the 'btech-project' root folder
    input_path = os.path.join("output", "cleaned_transcript.json")
    output_path = os.path.join("output", "entities.json")

    try:
        # 1. Load the cleaned transcript from Person 2
        if not os.path.exists(input_path):
            print(f"Error: {input_path} not found. Run Person 2's script first.")
            return

        with open(input_path, "r") as f:
            data = json.load(f)

        print("Starting BioBERT Entity Extraction...")
        
        # 2. Run the extraction logic
        # data["segments"] comes from the structure created in clean_transcript.py
        extracted_data = extract_with_biobert(data["segments"])

        # 3. Save the results for Person 4 (SOAP Generator)
        with open(output_path, "w") as f:
            json.dump(extracted_data, f, indent=4)

        print(f"Success! Medical entities saved to: {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()