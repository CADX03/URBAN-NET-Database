import requests

def get_timescale_data(entity_id=None, entity_type=None):
    """
    Retrieves time-series data from the QuantumLeap API (TimescaleDB).
    If entity_id is provided, gets historical data for that specific entity.
    If entity_id is None, retrieves historical data for all entities.
    """
    # Base URL for the QuantumLeap entities endpoint
    base_url = 'http://quantumleap:8668/v2/entities'
    
    query_params = {}

    if entity_id:
        # Construct URL for a specific entity ID
        url = f"{base_url}/{entity_id}"
    else:
        # Base URL to get all entities
        url = base_url
        # QuantumLeap doesn't strictly require 'type' to avoid a 400 error like Orion, 
        # but passing it helps keep massive database queries manageable!
        if entity_type:
            query_params['type'] = entity_type

    try:
        response = requests.get(url, params=query_params)
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to TimescaleDB: {e}")
        # Print detailed server error if available
        if e.response is not None and e.response.text:
            print(f"Server response details: {e.response.text}")
        return None

# --- Examples of how to use the function ---
if __name__ == "__main__":
    
    print("--- Fetching history for a specific ID ('Room2') ---")
    specific_id = "Room2"
    specific_data = get_timescale_data(entity_id=specific_id)
    print(specific_data)
    
    print("\n--- Fetching ALL historical data ---")
    # Calling without an ID gets all data. 
    # Optional: You can pass entity_type="Room" to filter the results.
    all_data = get_timescale_data() 
    print(all_data)