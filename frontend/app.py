
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="SmartCab",
    layout="wide"
)

# Session state
if "token" not in st.session_state:
    st.session_state.token = None


def login(username, password):
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={
                "email": username,
                "password": password,
                "company_id": 1
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.rerun()
        else:
            st.error("Invalid username or password.")

    except requests.RequestException:
        st.error("Unable to connect to the SmartCab server.")


# Login screen
if not st.session_state.token:

    st.title("SmartCab")
    st.caption("Intelligent AI Transportation")

    st.divider()

    _, center, _ = st.columns([1, 1.2, 1])

    with center:
        st.subheader("Welcome back")
        st.write("Sign in to access your SmartCab assistant.")

        username = st.text_input(
            "Username / Email",
            placeholder="employee@X.test"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Login", use_container_width=True):
            if username and password:
                with st.spinner("Authenticating..."):
                    login(username, password)
            else:
                st.warning("Please enter your credentials.")

else:
    st.success("Login successful!")
    st.write("Welcome to SmartCab.")
