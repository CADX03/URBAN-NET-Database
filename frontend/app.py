import streamlit as st
import pandas as pd
import os
import tempfile
from streamlit_oauth import OAuth2Component

from backend.getDataMongoDB import get_sensor_data
from backend.getDataTimescaleDB import get_timescale_data
from backend.sendDataMongoDB import send_data_to_broker
from backend.sendDataTimescaleDB import send_notification_to_quantumleap

# --- Keycloak Configuration ---

# 1. The Authorize URL goes to the user's web browser. 
# The browser is outside Docker, so it MUST use localhost.
AUTHORIZE_URL = "http://localhost:8080/realms/fiware-realm/protocol/openid-connect/auth"

# 2. The Token and Revoke URLs are used by the Streamlit Python backend.
# The backend is inside Docker, so it MUST use the Docker service name ('keycloak').
TOKEN_URL = "http://keycloak:8080/realms/fiware-realm/protocol/openid-connect/token"
REVOKE_URL = "http://keycloak:8080/realms/fiware-realm/protocol/openid-connect/logout"

CLIENT_ID = "streamlit-app"
CLIENT_SECRET = ""

st.set_page_config(page_title="URBAN-NET Database", layout="wide")

# Initialize the OAuth2 component
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

# --- Helper to handle file uploads for your functions ---
def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    return None

# Initialize session state for token
if "token" not in st.session_state:
    st.session_state["token"] = None

# ==========================================
# AUTHENTICATION ROUTING
# ==========================================

# 1. User is NOT logged in -> Show Login Page
if st.session_state["token"] is None:
    st.title("🔒 Login Required")
    st.info("Please authenticate via Keycloak to access the URBAN-NET Database.")
    
    # Render the login button
    result = oauth2.authorize_button(
        name="Login with Keycloak",
        redirect_uri="http://localhost:8501",
        scope="openid profile email"
    )
    
    if result and "token" in result:
        st.session_state["token"] = result.get("token")
        st.rerun()

# 2. User IS logged in -> Show Main Application
else:
    # Sidebar for user info and logout
    with st.sidebar:
        st.success("Authenticated ✅")
        if st.button("Logout"):
            st.session_state["token"] = None
            st.rerun()

    st.title("🎛️ URBAN-NET Database")

    # --- UI Layout ---
    tab1, tab2 = st.tabs(["📤 Send Data (Ingestion)", "📊 Get Data (Visualization)"])

    # === TAB 1: SEND DATA ===
    with tab1:
        st.header("Data Ingestion")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. Update Context (Orion)")
            st.info("Upload a JSON file to update entities in Orion-LD.")
            uploaded_orion = st.file_uploader("Choose Orion JSON", type=['json'], key="orion_up")
            
            if st.button("Send to Orion"):
                if uploaded_orion:
                    temp_path = save_uploaded_file(uploaded_orion)
                    try:
                        result = send_data_to_broker(temp_path) 
                        st.success(f"Success! Response: {result}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        os.remove(temp_path)
                else:
                    st.warning("Please upload a file first.")

        with col2:
            st.subheader("2. Configure Subscription (QuantumLeap)")
            st.info("Upload a JSON file to subscribe QuantumLeap to Orion changes.")
            uploaded_ql = st.file_uploader("Choose Subscription JSON", type=['json'], key="ql_up")
            
            if st.button("Send Notification/Sub"):
                if uploaded_ql:
                    temp_path = save_uploaded_file(uploaded_ql)
                    try:
                        result = send_notification_to_quantumleap(temp_path)
                        st.success(f"Subscription Created! Response: {result}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        os.remove(temp_path)
                else:
                    st.warning("Please upload a file first.")

    # === TAB 2: GET DATA ===
    with tab2:
        st.header("Data Visualization")
        
        with st.container():
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                entity_id = st.text_input("Entity ID", value="")
            with c2:
                entity_type = st.text_input("Entity Type", value="")
            with c3:
                st.write("") 
                st.write("") 
                refresh = st.button("Fetch Data")

        tab_realtime, tab_history = st.tabs(["⏱️ Current State (MongoDB)", "📈 History (TimescaleDB)"])

        if refresh:
            # --- Real-time Data (Orion) ---
            with tab_realtime:
                try:
                    current_data = get_sensor_data(entity_id=entity_id, entity_type=entity_type)
                    st.json(current_data)
                except Exception as e:
                    st.error(f"Could not fetch Orion data: {e}")

            # --- Historical Data (Timescale) ---
            with tab_history:
                try:
                    history_data = get_timescale_data(entity_id=entity_id, entity_type=entity_type)
                    
                    if history_data:
                        if not isinstance(history_data, pd.DataFrame):
                            df = pd.DataFrame(history_data)
                        else:
                            df = history_data
                        
                        st.dataframe(df.head())
                        
                        numeric_cols = df.select_dtypes(include=['float', 'int']).columns
                        if len(numeric_cols) > 0:
                            st.line_chart(df[numeric_cols])
                        else:
                            st.warning("No numeric data found to chart.")
                    else:
                        st.warning("No historical data found.")
                except Exception as e:
                    st.error(f"Could not fetch Timescale data: {e}")