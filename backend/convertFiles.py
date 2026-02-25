import json

def convert_file_to_ngsi_ld(input_path, output_path):
    try:
        # 1. Open and load the original JSON file
        with open(input_path, 'r') as file:
            data = json.load(file)
            
        # 2. Iterate through and update the attributes
        for entity in data:
            for key, value in entity.items():
                if isinstance(value, dict) and 'type' in value:
                    # Update the types
                    if value['type'] in ['Number', 'DateTime', 'Text', 'String']:
                        value['type'] = 'Property'
                    
                    # Clean up empty metadata
                    if 'metadata' in value and not value['metadata']:
                        del value['metadata']

        # 3. Save the updated data to the new file
        with open(output_path, 'w') as file:
            # indent=2 keeps the JSON nicely formatted and readable
            json.dump(data, file, indent=2)
            
        print(f"Success! The file has been converted and saved to:\n{output_path}")

    except FileNotFoundError:
        print(f"Error: The file '{input_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{input_path}' does not contain valid JSON.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Your current file
    input_file = './../data/weatherPortoHistorical.json'
    
    # The new file it will create
    output_file = './../data/weatherPortoHistorical_NGSILD.json'
    
    # If you want to overwrite the original file instead, 
    # just change output_file to equal input_file.
    
    convert_file_to_ngsi_ld(input_file, output_file)