import json
import requests
import time

def send_notification_to_quantumleap_in_batches(file_path, batch_size=500):
    # If running this script from your host machine, use localhost. 
    # If running from inside the frontend container, keep 'quantumleap'.
    url = 'http://quantumleap:8668/v2/notify' 
    
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        print(f"Reading file: {file_path} (This might take a moment for 80MB...)")
        with open(file_path, 'r') as file:
            raw_entities = json.load(file)
            
        # Ensure the data is a list so we can iterate over it
        if not isinstance(raw_entities, list):
            raw_entities = [raw_entities]

        total_entities = len(raw_entities)
        print(f"Successfully loaded {total_entities} entities. Starting batch upload...\n")

        # Chunk the data and send in batches
        for i in range(0, total_entities, batch_size):
            batch = raw_entities[i:i + batch_size]
            
            payload = {
                "data": batch
            }

            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code in [200, 201, 204]:
                print(f"[{i + len(batch)}/{total_entities}] Success! Batch sent.")
            else:
                print(f"Failed to send batch starting at index {i}. Status: {response.status_code}")
                print(f"Response: {response.text}")
                # Optional: break the loop if a batch fails, or continue to the next
                break 
            
            # Brief pause to let QuantumLeap and TimescaleDB breathe
            time.sleep(0.1) 

        print("\nFinished sending data.")

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' does not contain valid JSON.")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to QuantumLeap: {e}")

if __name__ == "__main__":
    # Point the function to your JSON file
    send_notification_to_quantumleap_in_batches('./../dataCSV/dataCSV_JSON/trafficflowobserved_part4.json', batch_size=500)