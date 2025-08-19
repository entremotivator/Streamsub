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

# Page configuration
st.set_page_config(
    page_title="AI PropIQ - Subscriber Access",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WordPressSubscriberAuth:
    def __init__(self):
        # Use Streamlit secrets for configuration
        self.base_url = st.secrets["wordpress"]["base_url"]
        self.consumer_key = st.secrets["woocommerce"]["consumer_key"]
        self.consumer_secret = st.secrets["woocommerce"]["consumer_secret"]
        self.jwt_secret = st.secrets["jwt"]["secret_key"]
        self.product_id = 190  # Set specific product ID as required
        
    def authenticate_user(self, username, password):
        """Authenticate user with WordPress"""
        auth_url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
        
        try:
            response = requests.post(auth_url, json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'token': data.get('token'),
                    'user_email': data.get('user_email'),
                    'user_nicename': data.get('user_nicename'),
                    'user_display_name': data.get('user_display_name'),
                    'user_id': data.get('user_id')
                }
            else:
                return {'success': False, 'message': 'Invalid credentials'}
                
        except Exception as e:
            return {'success': False, 'message': f'Authentication error: {str(e)}'}
    
    def check_subscriber_status(self, user_email):
        """Check if user has WordPress subscriber role"""
        try:
            users_url = f"{self.base_url}/wp-json/wp/v2/users"
            
            response = requests.get(
                users_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'search': user_email}
            )
            
            if response.status_code == 200:
                users = response.json()
                
                for user in users:
                    if user.get('email') == user_email:
                        roles = user.get('roles', [])
                        if 'subscriber' in roles:
                            return {
                                'is_subscriber': True,
                                'user_id': user.get('id'),
                                'username': user.get('username'),
                                'email': user.get('email'),
                                'roles': roles
                            }
                        
                return {'is_subscriber': False, 'message': 'User does not have subscriber role'}
            else:
                return {'is_subscriber': False, 'message': f"API Error: {response.status_code}"}
                
        except Exception as e:
            return {'is_subscriber': False, 'message': f'Error checking subscriber status: {str(e)}'}
    
    def get_customer_by_email(self, email):
        """Get WooCommerce customer by email"""
        try:
            customers_url = f"{self.base_url}/wp-json/wc/v3/customers"
            
            response = requests.get(
                customers_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'email': email}
            )
            
            if response.status_code == 200:
                customers = response.json()
                if customers:
                    return customers[0]  # Return first matching customer
                return None
                
        except Exception as e:
            st.error(f"Error fetching customer: {str(e)}")
            return None
    
    def get_product_info(self, product_id):
        """Get specific product information"""
        try:
            product_url = f"{self.base_url}/wp-json/wc/v3/products/{product_id}"
            
            response = requests.get(
                product_url,
                auth=(self.consumer_key, self.consumer_secret)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            st.error(f"Error fetching product: {str(e)}")
            return None
    
    def get_customer_orders(self, customer_id):
        """Get orders for specific customer"""
        try:
            orders_url = f"{self.base_url}/wp-json/wc/v3/orders"
            
            response = requests.get(
                orders_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'customer': customer_id}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            st.error(f"Error fetching orders: {str(e)}")
            return []

def redirect_to_home():
    """Redirect non-subscribers to aipropiq.com"""
    st.error("Access Denied: Subscriber access required")
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h3>🚫 Access Restricted</h3>
        <p>This area is restricted to WordPress subscribers only.</p>
        <p>Redirecting to home page...</p>
        <script>
            setTimeout(function() {
                window.location.href = "https://aipropiq.com";
            }, 3000);
        </script>
    </div>
    """, unsafe_allow_html=True)
    
    # Alternative redirect method for Streamlit
    st.markdown("""
    <meta http-equiv="refresh" content="3;url=https://aipropiq.com">
    """, unsafe_allow_html=True)

def apply_custom_css():
    """Apply custom CSS styling"""
    st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .login-container {
        background: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        max-width: 500px;
        margin: 0 auto;
    }
    
    .subscriber-dashboard {
        background: rgba(255, 255, 255, 0.9);
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    .product-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        margin: 1rem 0;
    }
    
    .payment-info {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #4CAF50;
    }
    
    .access-denied {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin: 2rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

def login_page():
    """Display subscriber login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("# 🏠 AI PropIQ")
    st.markdown("### Subscriber Access Portal")
    st.markdown("Please login with your WordPress subscriber credentials")
    
    with st.form("subscriber_login_form"):
        username = st.text_input("Username", placeholder="Enter your WordPress username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button("Login as Subscriber")
        
        if submit_button:
            if username and password:
                auth = WordPressSubscriberAuth()
                
                # Authenticate user
                auth_result = auth.authenticate_user(username, password)
                
                if auth_result['success']:
                    # Check subscriber status
                    subscriber_status = auth.check_subscriber_status(auth_result['user_email'])
                    
                    if subscriber_status.get('is_subscriber'):
                        # Get customer info from WooCommerce
                        customer_info = auth.get_customer_by_email(auth_result['user_email'])
                        
                        if customer_info:
                            # Store session data
                            st.session_state.authenticated = True
                            st.session_state.user_data = auth_result
                            st.session_state.subscriber_data = subscriber_status
                            st.session_state.customer_data = customer_info
                            st.session_state.product_id = auth.product_id
                            
                            st.success("✅ Subscriber login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("WordPress subscriber verified, but no WooCommerce customer record found.")
                            # Still allow access for WordPress subscribers
                            st.session_state.authenticated = True
                            st.session_state.user_data = auth_result
                            st.session_state.subscriber_data = subscriber_status
                            st.session_state.customer_data = None
                            st.session_state.product_id = auth.product_id
                            st.rerun()
                    else:
                        st.error("❌ Access denied: WordPress subscriber role required")
                        st.info("Redirecting to aipropiq.com...")
                        time.sleep(2)
                        redirect_to_home()
                else:
                    st.error(f"❌ Login failed: {auth_result['message']}")
            else:
                st.error("Please enter both username and password")
    
    st.markdown('</div>', unsafe_allow_html=True)

def subscriber_dashboard():
    """Display subscriber dashboard with product and payment info"""
    st.markdown("# 🏠 AI PropIQ - Subscriber Dashboard")
    st.markdown(f"Welcome, **{st.session_state.user_data['user_display_name']}**!")
    
    auth = WordPressSubscriberAuth()
    
    # Display subscriber status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="product-card">
            <h3>✅ Subscriber Status</h3>
            <h2>Active</h2>
            <p>WordPress Subscriber</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="product-card">
            <h3>🎯 Product ID</h3>
            <h2>{st.session_state.product_id}</h2>
            <p>Assigned Product</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        user_roles = ', '.join(st.session_state.subscriber_data.get('roles', []))
        st.markdown(f"""
        <div class="product-card">
            <h3>👤 User Role</h3>
            <h2>Subscriber</h2>
            <p>{user_roles}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Product Information Section
    st.markdown("## 🛍️ Product Information")
    
    product_info = auth.get_product_info(st.session_state.product_id)
    
    if product_info:
        st.markdown(f"""
        <div class="subscriber-dashboard">
            <h3>{product_info.get('name', 'Product Name')}</h3>
            <p><strong>Price:</strong> ${product_info.get('price', '0')}</p>
            <p><strong>Regular Price:</strong> ${product_info.get('regular_price', '0')}</p>
            <p><strong>Status:</strong> {product_info.get('status', 'Unknown').title()}</p>
            <p><strong>Description:</strong> {product_info.get('short_description', 'No description available')}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(f"Product ID {st.session_state.product_id} not found or inaccessible")
    
    # Payment Information Section
    if st.session_state.customer_data:
        st.markdown("## 💳 Payment Information")
        
        customer = st.session_state.customer_data
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="payment-info">
                <h4>Customer Details</h4>
                <p><strong>Name:</strong> {customer.get('first_name', '')} {customer.get('last_name', '')}</p>
                <p><strong>Email:</strong> {customer.get('email', '')}</p>
                <p><strong>Total Orders:</strong> {customer.get('orders_count', 0)}</p>
                <p><strong>Total Spent:</strong> ${customer.get('total_spent', '0')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Get customer orders
            orders = auth.get_customer_orders(customer.get('id'))
            
            if orders:
                latest_order = orders[0]  # Most recent order
                st.markdown(f"""
                <div class="payment-info">
                    <h4>Latest Order</h4>
                    <p><strong>Order ID:</strong> #{latest_order.get('id', 'N/A')}</p>
                    <p><strong>Status:</strong> {latest_order.get('status', 'Unknown').title()}</p>
                    <p><strong>Total:</strong> ${latest_order.get('total', '0')}</p>
                    <p><strong>Date:</strong> {latest_order.get('date_created', '').split('T')[0] if latest_order.get('date_created') else 'N/A'}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="payment-info">
                    <h4>Order History</h4>
                    <p>No orders found</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Orders table
        if orders:
            st.markdown("### 📦 Order History")
            
            order_data = []
            for order in orders:
                order_data.append({
                    'Order ID': order.get('id'),
                    'Status': order.get('status', '').title(),
                    'Total': f"${order.get('total', 0)}",
                    'Payment Method': order.get('payment_method_title', 'N/A'),
                    'Date': order.get('date_created', '').split('T')[0] if order.get('date_created') else 'N/A'
                })
            
            df_orders = pd.DataFrame(order_data)
            st.dataframe(df_orders, use_container_width=True)
    
    else:
        st.info("No WooCommerce customer data available. WordPress subscriber access confirmed.")

def main():
    """Main application function"""
    apply_custom_css()
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Check authentication
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Sidebar for authenticated subscribers
    with st.sidebar:
        st.markdown("# 🏠 AI PropIQ")
        st.markdown(f"**Subscriber:** {st.session_state.user_data['user_display_name']}")
        st.markdown(f"**Email:** {st.session_state.user_data['user_email']}")
        st.markdown(f"**Product ID:** {st.session_state.product_id}")
        st.markdown("---")
        
        st.markdown("### 📊 Quick Stats")
        if st.session_state.customer_data:
            st.metric("Total Orders", st.session_state.customer_data.get('orders_count', 0))
            st.metric("Total Spent", f"${st.session_state.customer_data.get('total_spent', '0')}")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Display subscriber dashboard
    subscriber_dashboard()

if __name__ == "__main__":
    main()
