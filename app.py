import streamlit as st
import requests
import json
import jwt
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
from io import BytesIO
import time
import hashlib
import secrets
import string

# Page configuration
st.set_page_config(
    page_title="AI PropIQ - WordPress Admin & Subscriber Portal",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WordPressAdminManager:
    def __init__(self):
        # Use Streamlit secrets for configuration
        self.base_url = st.secrets["wordpress"]["base_url"]
        self.consumer_key = st.secrets["woocommerce"]["consumer_key"]
        self.consumer_secret = st.secrets["woocommerce"]["consumer_secret"]
        self.jwt_secret = st.secrets["jwt"]["secret_key"]
        self.admin_username = st.secrets.get("wordpress", {}).get("admin_username", "admin")
        self.admin_password = st.secrets.get("wordpress", {}).get("admin_password", "")
        self.product_id = 190  # Set specific product ID as required
        
    def authenticate_user(self, username, password):
        """Authenticate user with WordPress using JWT with enhanced error handling"""
        auth_url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
        
        # Debug information
        st.write(f"[DEBUG] Attempting JWT authentication to: {auth_url}")
        st.write(f"[DEBUG] Username: {username}")
        
        try:
            # Prepare authentication payload
            auth_payload = {
                'username': username,
                'password': password
            }
            
            # Set proper headers
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            st.write(f"[DEBUG] Sending request with payload: {json.dumps(auth_payload, indent=2)}")
            
            # Make the authentication request
            response = requests.post(
                auth_url, 
                json=auth_payload,
                headers=headers,
                timeout=30  # Add timeout
            )
            
            st.write(f"[DEBUG] Response status code: {response.status_code}")
            st.write(f"[DEBUG] Response headers: {dict(response.headers)}")
            
            # Log the raw response
            try:
                response_text = response.text
                st.write(f"[DEBUG] Raw response: {response_text}")
            except Exception as e:
                st.write(f"[DEBUG] Could not read response text: {str(e)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    st.write(f"[DEBUG] Parsed JSON response: {json.dumps(data, indent=2)}")
                    
                    # Validate JWT token if present
                    token = data.get('token')
                    if token:
                        try:
                            # Decode JWT token to verify it's valid
                            decoded_token = jwt.decode(
                                token, 
                                self.jwt_secret, 
                                algorithms=['HS256'],
                                options={"verify_exp": False}  # Don't verify expiration for now
                            )
                            st.write(f"[DEBUG] Decoded JWT token: {json.dumps(decoded_token, indent=2)}")
                            
                        except jwt.InvalidTokenError as jwt_error:
                            st.warning(f"[DEBUG] JWT token validation failed: {str(jwt_error)}")
                            # Continue anyway, token might still work for API calls
                    
                    return {
                        'success': True,
                        'token': data.get('token'),
                        'user_email': data.get('user_email'),
                        'user_nicename': data.get('user_nicename'),
                        'user_display_name': data.get('user_display_name'),
                        'user_id': data.get('user_id'),
                        'raw_response': data
                    }
                    
                except json.JSONDecodeError as json_error:
                    st.error(f"[DEBUG] JSON decode error: {str(json_error)}")
                    return {
                        'success': False, 
                        'message': f'Invalid JSON response from server: {str(json_error)}',
                        'raw_response': response.text
                    }
                    
            elif response.status_code == 403:
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Authentication forbidden')
                    st.error(f"[DEBUG] 403 Forbidden: {error_message}")
                    
                    # Check if JWT plugin is active
                    if 'jwt-auth' in error_message.lower() or 'forbidden' in error_message.lower():
                        return {
                            'success': False, 
                            'message': 'JWT Authentication plugin may not be installed or configured properly on WordPress',
                            'suggestion': 'Please ensure JWT Authentication for WP-API plugin is installed and configured'
                        }
                    else:
                        return {'success': False, 'message': error_message}
                        
                except json.JSONDecodeError:
                    return {
                        'success': False, 
                        'message': 'Authentication forbidden - JWT plugin may not be configured',
                        'raw_response': response.text
                    }
                    
            elif response.status_code == 404:
                return {
                    'success': False, 
                    'message': 'JWT endpoint not found - JWT Authentication plugin may not be installed',
                    'suggestion': 'Install and activate "JWT Authentication for WP-API" plugin'
                }
                
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', f'HTTP {response.status_code} error')
                    return {'success': False, 'message': error_message}
                except json.JSONDecodeError:
                    return {
                        'success': False, 
                        'message': f'HTTP {response.status_code}: {response.text}',
                        'raw_response': response.text
                    }
                
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Request timeout - server may be slow or unreachable'}
            
        except requests.exceptions.ConnectionError:
            return {'success': False, 'message': 'Connection error - check if WordPress site is accessible'}
            
        except requests.exceptions.RequestException as req_error:
            return {'success': False, 'message': f'Request error: {str(req_error)}'}
            
        except Exception as e:
            st.error(f"[DEBUG] Unexpected error: {str(e)}")
            return {'success': False, 'message': f'Unexpected authentication error: {str(e)}'}
    
    def test_jwt_endpoint(self):
        """Test if JWT endpoint is accessible"""
        test_url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
        
        try:
            # Try a simple GET request to see if endpoint exists
            response = requests.get(test_url, timeout=10)
            
            if response.status_code == 405:  # Method not allowed is expected for GET on POST endpoint
                return {'accessible': True, 'message': 'JWT endpoint is accessible'}
            elif response.status_code == 404:
                return {'accessible': False, 'message': 'JWT endpoint not found - plugin may not be installed'}
            else:
                return {'accessible': True, 'message': f'JWT endpoint responded with status {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            return {'accessible': False, 'message': f'Cannot reach JWT endpoint: {str(e)}'}
    
    def authenticate_with_basic_auth(self, username, password):
        """Fallback authentication using WordPress REST API basic auth"""
        try:
            # Try to get user info using basic auth
            users_url = f"{self.base_url}/wp-json/wp/v2/users/me"
            
            response = requests.get(
                users_url,
                auth=(username, password),
                timeout=30
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'success': True,
                    'user_email': user_data.get('email'),
                    'user_nicename': user_data.get('slug'),
                    'user_display_name': user_data.get('name'),
                    'user_id': user_data.get('id'),
                    'auth_method': 'basic_auth'
                }
            else:
                return {'success': False, 'message': 'Basic authentication failed'}
                
        except Exception as e:
            return {'success': False, 'message': f'Basic auth error: {str(e)}'}


def login_page():
    """Display enhanced login page with admin/subscriber options and JWT debugging"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("# 🏠 AI PropIQ")
    st.markdown("### WordPress Admin & Subscriber Portal")
    
    admin_manager = WordPressAdminManager()
    
    # Test JWT endpoint accessibility
    with st.expander("🔧 JWT Connection Diagnostics", expanded=False):
        if st.button("Test JWT Endpoint"):
            jwt_test = admin_manager.test_jwt_endpoint()
            if jwt_test['accessible']:
                st.success(f"✅ {jwt_test['message']}")
            else:
                st.error(f"❌ {jwt_test['message']}")
                st.info("💡 Try installing 'JWT Authentication for WP-API' plugin on your WordPress site")
        
        st.markdown("**Expected JWT Endpoint:** `/wp-json/jwt-auth/v1/token`")
        st.markdown(f"**Full URL:** `{admin_manager.base_url}/wp-json/jwt-auth/v1/token`")
    
    # Login type selection
    login_type = st.radio("Select Login Type:", ["Subscriber Access", "Admin Panel"], horizontal=True)
    
    auth_method = st.radio("Authentication Method:", ["JWT (Recommended)", "Basic Auth (Fallback)"], horizontal=True)
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your WordPress username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        debug_mode = st.checkbox("Enable Debug Mode", help="Show detailed authentication logs")
        
        submit_button = st.form_submit_button(f"Login as {login_type.split()[0]}")
        
        if submit_button:
            if username and password:
                
                # Choose authentication method
                if auth_method == "JWT (Recommended)":
                    auth_result = admin_manager.authenticate_user(username, password)
                else:
                    auth_result = admin_manager.authenticate_with_basic_auth(username, password)
                
                # Show debug information if enabled
                if debug_mode and not auth_result['success']:
                    st.error("Authentication failed. Debug information:")
                    st.json(auth_result)
                    
                    if 'suggestion' in auth_result:
                        st.info(f"💡 Suggestion: {auth_result['suggestion']}")
                
                if auth_result['success']:
                    if login_type == "Admin Panel":
                        # Check for admin role
                        role_check = admin_manager.check_user_role(auth_result['user_email'], 'administrator')
                        
                        if role_check.get('is_admin'):
                            # Store admin session data
                            st.session_state.authenticated = True
                            st.session_state.is_admin = True
                            st.session_state.user_data = auth_result
                            st.session_state.role_data = role_check
                            
                            st.success("✅ Admin login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Access denied: Administrator role required for admin panel")
                    
                    else:  # Subscriber Access
                        # Check subscriber status
                        subscriber_status = admin_manager.check_user_role(auth_result['user_email'], 'subscriber')
                        
                        if subscriber_status.get('has_role'):
                            # Get customer info from WooCommerce
                            customer_info = admin_manager.get_customer_by_email(auth_result['user_email'])
                            
                            # Store session data
                            st.session_state.authenticated = True
                            st.session_state.is_admin = False
                            st.session_state.user_data = auth_result
                            st.session_state.subscriber_data = subscriber_status
                            st.session_state.customer_data = customer_info
                            st.session_state.product_id = admin_manager.product_id
                            
                            st.success("✅ Subscriber login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Access denied: WordPress subscriber role required")
                            st.info("Redirecting to aipropiq.com...")
                            time.sleep(2)
                            redirect_to_home()
                else:
                    error_message = auth_result.get('message', 'Unknown authentication error')
                    st.error(f"❌ Login failed: {error_message}")
                    
                    if 'jwt' in error_message.lower() or 'plugin' in error_message.lower():
                        st.warning("🔧 **JWT Setup Required:**")
                        st.markdown("""
                        1. Install 'JWT Authentication for WP-API' plugin on WordPress
                        2. Add JWT secret key to wp-config.php:
                           ```php
                           define('JWT_AUTH_SECRET_KEY', 'your-secret-key');
