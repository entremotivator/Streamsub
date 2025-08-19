import streamlit as st
import requests
import json
import jwt
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="AI PropIQ - WordPress Admin & Subscriber Portal",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)


class WordPressAdminManager:
    """Manage WordPress/WooCommerce authentication and user role checks"""

    def __init__(self):
        # Safe secret loading with defaults
        self.base_url = st.secrets.get("wordpress", {}).get("base_url", "")
        self.consumer_key = st.secrets.get("woocommerce", {}).get("consumer_key", "")
        self.consumer_secret = st.secrets.get("woocommerce", {}).get("consumer_secret", "")
        self.jwt_secret = st.secrets.get("jwt", {}).get("secret_key", "")
        self.admin_username = st.secrets.get("wordpress", {}).get("admin_username", "admin")
        self.admin_password = st.secrets.get("wordpress", {}).get("admin_password", "")
        self.product_id = 190  # Product to check subscription access

        if not self.base_url:
            st.error("❌ Missing WordPress base URL in secrets.toml")
            st.stop()

    def authenticate_user(self, username, password):
        """Authenticate user with WordPress using JWT"""
        auth_url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
        try:
            response = requests.post(auth_url, json={"username": username, "password": password}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return {"success": True, **data}
            return {"success": False, "message": response.text}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def authenticate_with_basic_auth(self, username, password):
        """Fallback authentication using basic auth"""
        users_url = f"{self.base_url}/wp-json/wp/v2/users/me"
        try:
            response = requests.get(users_url, auth=(username, password), timeout=30)
            if response.status_code == 200:
                return {"success": True, **response.json()}
            return {"success": False, "message": response.text}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def check_user_role(self, email, role_name):
        """Check if WordPress user has a given role"""
        try:
            url = f"{self.base_url}/wp-json/wp/v2/users?search={email}"
            response = requests.get(url, auth=(self.admin_username, self.admin_password), timeout=30)
            if response.status_code == 200:
                users = response.json()
                if users:
                    roles = users[0].get("roles", [])
                    return {"has_role": role_name in roles, "is_admin": "administrator" in roles}
            return {"has_role": False, "is_admin": False}
        except Exception as e:
            return {"has_role": False, "is_admin": False, "error": str(e)}

    def get_customer_by_email(self, email):
        """Fetch WooCommerce customer info"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/customers"
            response = requests.get(
                url,
                params={"email": email},
                auth=(self.consumer_key, self.consumer_secret),
                timeout=30
            )
            if response.status_code == 200:
                customers = response.json()
                return customers[0] if customers else {}
            return {}
        except Exception as e:
            return {}


def redirect_to_home():
    """Redirect user to homepage"""
    st.markdown("Redirecting to [AIPropIQ](https://aipropiq.com) ...")
    st.stop()


def login_page():
    """Display the login page for subscribers and admin"""
    st.markdown("# 🏠 AI PropIQ")
    st.markdown("### WordPress Admin & Subscriber Portal")

    admin_manager = WordPressAdminManager()

    login_type = st.radio("Select Login Type:", ["Subscriber Access", "Admin Panel"], horizontal=True)
    auth_method = st.radio("Authentication Method:", ["JWT (Recommended)", "Basic Auth (Fallback)"], horizontal=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button and username and password:
            if auth_method == "JWT (Recommended)":
                auth_result = admin_manager.authenticate_user(username, password)
            else:
                auth_result = admin_manager.authenticate_with_basic_auth(username, password)

            if auth_result.get("success"):
                user_email = auth_result.get("user_email") or username

                if login_type == "Admin Panel":
                    role_check = admin_manager.check_user_role(user_email, "administrator")
                    if role_check.get("is_admin"):
                        st.session_state.authenticated = True
                        st.session_state.is_admin = True
                        st.session_state.user_data = auth_result
                        st.success("✅ Admin login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Admin role required")
                else:
                    role_check = admin_manager.check_user_role(user_email, "subscriber")
                    if role_check.get("has_role"):
                        customer_info = admin_manager.get_customer_by_email(user_email)
                        st.session_state.authenticated = True
                        st.session_state.is_admin = False
                        st.session_state.user_data = auth_result
                        st.session_state.customer_data = customer_info
                        st.success("✅ Subscriber login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Subscriber role required")
                        time.sleep(2)
                        redirect_to_home()
            else:
                st.error(f"❌ Login failed: {auth_result.get('message')}")


if __name__ == "__main__":
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    login_page()
