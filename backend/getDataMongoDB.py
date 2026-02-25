import requests

def get_sensor_data(entity_id=None, entity_type=None):
    """
    Retrieves data from the NGSI-LD API.
    If entity_id is provided, gets that specific entity.
    If entity_id is None, retrieves all entities of the specified entity_type.
    """
    base_url = 'http://orion:1026/ngsi-ld/v1/entities'
    
    # We will use this dictionary to handle our query parameters securely
    query_params = {}

    if entity_id:
        # If we have an ID, we append it directly to the URL path
        url = f"{base_url}/{entity_id}"
    else:
        # If we don't have an ID, we query the base URL but MUST provide a type
        url = base_url
        query_params['type'] = entity_type

    try:
        # The 'params' argument automatically safely formats the URL for us 
        # (e.g., adding ?type=Sensor to the end of the URL)
        response = requests.get(url, params=query_params)
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to the API: {e}")
        # Print the exact response text from the server to help with future debugging
        if response is not None and response.text:
            print(f"Server response details: {response.text}")
        return None

# --- Examples of how to use the function ---
if __name__ == "__main__":
    
    print("--- Fetching a specific ID ---")
    specific_id = "urn:ngsi-ld:Sensor:001"
    specific_data = get_sensor_data(entity_id=specific_id)
    print(specific_data)
    
    print("\n--- Fetching ALL data of type 'Sensor' ---")
    # Calling the function without an ID defaults to getting all 'Sensor' types
    all_data = get_sensor_data() 
    print(all_data)