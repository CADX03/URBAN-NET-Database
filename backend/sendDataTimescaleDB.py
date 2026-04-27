import json
import requests
import time

def send_notification_to_quantumleap_in_batches(file_path, batch_size=500):
    start_time = time.perf_counter()

    # If running this script from your host machine, use localhost. 
    # If running from inside the frontend container, keep 'quantumleap'.
    url = 'http://quantumleap:8668/v2/notify' 
    #url = 'http://localhost:8668/v2/notify' 
    
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
        batches_sent = 0
        print(f"Successfully loaded {total_entities} entities. Starting batch upload...\n")

        # Chunk the data and send in batches
        for i in range(0, total_entities, batch_size):
            batch = raw_entities[i:i + batch_size]
            
            payload = {
                "data": batch
            }

            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code in [200, 201, 204]:
                batches_sent += 1
            else:
                # If a batch fails, stop everything and raise an error to the frontend
                print(f"Failed at batch starting at index {i}. Status: {response.status_code}. Response: {response.text}")
                raise Exception(f"Failed at batch starting at index {i}. Status: {response.status_code}. Response: {response.text}")
            
            # Brief pause to let QuantumLeap and TimescaleDB breathe
            time.sleep(0.1) 

        elapsed_time = time.perf_counter() - start_time
        # If the loop finishes without raising an exception, return a success summary
        print(f"All batches sent successfully! Total entities: {total_entities}, Total batches: {batches_sent}. Time taken: {elapsed_time:.2f}s")
        return f"Successfully sent {total_entities} entities across {batches_sent} batches to QuantumLeap in {elapsed_time:.2f} seconds."

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        raise Exception(f"The file '{file_path}' was not found.")
    
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' does not contain valid JSON.")
        raise Exception(f"The file '{file_path}' does not contain valid JSON.")
    
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to QuantumLeap: {e}")
        raise Exception(f"Error connecting to QuantumLeap: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise Exception(f"An unexpected error occurred: {e}")
    
if __name__ == "__main__":
    # Point the function to your JSON file
    #send_notification_to_quantumleap_in_batches('./../dataGTFS/ngsi_ld_converted_data/routes.json', batch_size=500)
    #send_notification_to_quantumleap_in_batches('./../dataGTFS/ngsi_ld_converted_data/calendar.json', batch_size=500)
    send_notification_to_quantumleap_in_batches('./../output/converted_geojson.json', batch_size=500)