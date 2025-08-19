import streamlit as st
import requests
import pandas as pd
import json
import hashlib
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import time
import base64
import numpy as np

# Page configuration
st.set_page_config(
    page_title="AI PropIQ Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .section-header {
        font-size: 1.8rem;
        color: #4682B4;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #4682B4;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .user-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        color: white;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
        background-color: #d4edda;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
        background-color: #f8d7da;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    .premium-badge {
        background: linear-gradient(45deg, #FFD700, #FFA500);
        color: #000;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .sidebar-logo {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

class WordPressWooCommerceAPI:
    def __init__(self, base_url: str, consumer_key: str, consumer_secret: str):
        self.base_url = base_url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth = (consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """Authenticate user with WordPress JWT"""
        try:
            # Use WordPress JWT Authentication
            url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
            payload = {
                "username": username,
                "password": password
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                user_id = token_data.get('user_id')
                
                if user_id:
                    # Get user details from WordPress
                    user_details = self.get_wordpress_user(user_id)
                    if user_details['success']:
                        user_info = user_details['data']
                        
                        # Check WooCommerce subscription status
                        subscription_info = self.check_user_subscription(user_id, product_id=190)
                        
                        return {
                            'success': True,
                            'user': {
                                'id': user_id,
                                'name': user_info.get('name', f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}").strip(),
                                'email': user_info.get('email', ''),
                                'username': user_info.get('username', username),
                                'role': self.determine_user_role(user_info, subscription_info),
                                'subscription_status': subscription_info.get('status', 'inactive'),
                                'subscription_product_id': 190 if subscription_info.get('has_subscription') else None,
                                'customer_id': user_info.get('id'),
                                'wordpress_roles': user_info.get('roles', []),
                                'token': token_data.get('token')
                            },
                            'message': 'Authentication successful'
                        }
            
            return {'success': False, 'error': 'Invalid username or password'}
            
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Connection error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Authentication error: {str(e)}'}
    
    def get_wordpress_user(self, user_id: int) -> Dict:
        """Get WordPress user information"""
        try:
            url = f"{self.base_url}/wp-json/wp/v2/users/{user_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                return {'success': True, 'data': user_data}
            else:
                return {'success': False, 'error': f'User not found: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def determine_user_role(self, user_info: dict, subscription_info: dict) -> str:
        """Determine user role based on WordPress roles and subscription status"""
        wordpress_roles = user_info.get('roles', [])
        
        if 'administrator' in wordpress_roles:
            return 'administrator'
        elif subscription_info.get('has_subscription') and subscription_info.get('status') == 'active':
            return 'subscriber'
        else:
            return 'customer'
    
    def check_user_subscription(self, user_id: int, product_id: int = 190) -> Dict:
        """Check if user has active subscription for specific product"""
        try:
            # Get customer by user ID first
            customer_info = self.get_customer_by_user_id(user_id)
            if not customer_info['success']:
                return {'has_subscription': False, 'status': 'inactive'}
            
            customer_id = customer_info['data']['id']
            
            # Get subscriptions for this customer
            url = f"{self.base_url}/wp-json/wc/v3/subscriptions"
            params = {
                'customer': customer_id,
                'per_page': 100
            }
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                subscriptions = response.json()
                
                # Check for active subscriptions with product ID 190
                for subscription in subscriptions:
                    if subscription.get('status') == 'active':
                        for item in subscription.get('line_items', []):
                            if item.get('product_id') == product_id:
                                return {
                                    'has_subscription': True,
                                    'status': 'active',
                                    'subscription_id': subscription.get('id'),
                                    'next_payment': subscription.get('next_payment_date'),
                                    'total': subscription.get('total')
                                }
                
                return {'has_subscription': False, 'status': 'inactive'}
            else:
                return {'has_subscription': False, 'status': 'inactive', 'error': f'API Error: {response.status_code}'}
                
        except Exception as e:
            return {'has_subscription': False, 'status': 'inactive', 'error': str(e)}
    
    def get_customer_by_user_id(self, user_id: int) -> Dict:
        """Get WooCommerce customer by WordPress user ID"""
        try:
            # First try to get customer by user ID meta
            url = f"{self.base_url}/wp-json/wc/v3/customers"
            params = {
                'search': str(user_id),
                'per_page': 100
            }
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                customers = response.json()
                
                # Find customer with matching user ID
                for customer in customers:
                    if customer.get('id') == user_id or str(customer.get('meta_data', {}).get('_user_id')) == str(user_id):
                        return {'success': True, 'data': customer}
                
                # If no direct match, try by email from WordPress user
                wp_user = self.get_wordpress_user(user_id)
                if wp_user['success']:
                    email = wp_user['data'].get('email')
                    if email:
                        params = {'email': email}
                        response = self.session.get(url, params=params, timeout=10)
                        if response.status_code == 200:
                            customers = response.json()
                            if customers:
                                return {'success': True, 'data': customers[0]}
            
            return {'success': False, 'error': 'Customer not found'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_users_with_subscriptions(self) -> Dict:
        """Get all users with their subscription information"""
        try:
            # Get all customers from WooCommerce
            all_customers = []
            page = 1
            per_page = 100
            
            while True:
                url = f"{self.base_url}/wp-json/wc/v3/customers"
                params = {'page': page, 'per_page': per_page}
                response = self.session.get(url, params=params, timeout=10)
                
                if response.status_code != 200:
                    break
                
                customers = response.json()
                if not customers:
                    break
                
                all_customers.extend(customers)
                
                # Check if we got less than per_page results (last page)
                if len(customers) < per_page:
                    break
                
                page += 1
            
            # Get subscription information for each customer
            customers_with_subs = []
            for customer in all_customers:
                customer_id = customer['id']
                
                # Get subscriptions for this customer
                sub_url = f"{self.base_url}/wp-json/wc/v3/subscriptions"
                sub_params = {'customer': customer_id}
                sub_response = self.session.get(sub_url, params=sub_params, timeout=10)
                
                customer_data = {
                    'id': customer_id,
                    'email': customer['email'],
                    'first_name': customer['first_name'],
                    'last_name': customer['last_name'],
                    'username': customer.get('username', ''),
                    'role': 'customer',
                    'date_created': customer['date_created'],
                    'orders_count': customer['orders_count'],
                    'total_spent': customer['total_spent'],
                    'subscriptions': []
                }
                
                if sub_response.status_code == 200:
                    subscriptions = sub_response.json()
                    
                    for subscription in subscriptions:
                        # Check if subscription has product ID 190
                        has_product_190 = False
                        for item in subscription.get('line_items', []):
                            if item.get('product_id') == 190:
                                has_product_190 = True
                                break
                        
                        if has_product_190:
                            customer_data['role'] = 'subscriber' if subscription.get('status') == 'active' else 'customer'
                            customer_data['subscriptions'].append({
                                'id': subscription['id'],
                                'status': subscription['status'],
                                'product_id': 190,
                                'total': subscription['total'],
                                'start_date': subscription['date_created'],
                                'next_payment': subscription.get('next_payment_date'),
                                'billing_period': subscription.get('billing_period'),
                                'billing_interval': subscription.get('billing_interval')
                            })
                
                customers_with_subs.append(customer_data)
            
            return {'success': True, 'data': customers_with_subs}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_products(self, per_page: int = 10, page: int = 1) -> Dict:
        """Fetch products from WooCommerce"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/products"
            params = {
                'per_page': per_page,
                'page': page,
                'status': 'publish'
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json(),
                'total_pages': int(response.headers.get('X-WP-TotalPages', 1)),
                'total_items': int(response.headers.get('X-WP-Total', 0))
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_subscriptions(self, per_page: int = 10, page: int = 1, product_id: int = None) -> Dict:
        """Fetch subscriptions from WooCommerce with optional product filter"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/subscriptions"
            params = {
                'per_page': per_page,
                'page': page
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            subscriptions = response.json()
            
            # Filter by product ID if specified
            if product_id:
                filtered_subs = []
                for sub in subscriptions:
                    for item in sub.get('line_items', []):
                        if item.get('product_id') == product_id:
                            filtered_subs.append(sub)
                            break
                subscriptions = filtered_subs
            
            return {
                'success': True,
                'data': subscriptions,
                'total_pages': int(response.headers.get('X-WP-TotalPages', 1)),
                'total_items': int(response.headers.get('X-WP-Total', 0))
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_customers(self, per_page: int = 10, page: int = 1) -> Dict:
        """Fetch customers from WooCommerce"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/customers"
            params = {
                'per_page': per_page,
                'page': page
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json(),
                'total_pages': int(response.headers.get('X-WP-TotalPages', 1)),
                'total_items': int(response.headers.get('X-WP-Total', 0))
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_connection(self) -> Dict:
        """Test API connection"""
        try:
            # Test WooCommerce API
            url = f"{self.base_url}/wp-json/wc/v3/system_status"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Also test WordPress API
                wp_url = f"{self.base_url}/wp-json/wp/v2/users/me"
                wp_response = self.session.get(wp_url, timeout=10)
                
                return {
                    'success': True, 
                    'message': 'WooCommerce and WordPress APIs connected successfully!',
                    'woocommerce_status': 'Connected',
                    'wordpress_status': 'Connected' if wp_response.status_code in [200, 401] else 'Limited'
                }
            else:
                return {'success': False, 'error': f'Connection failed with status {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    if 'api_configured' not in st.session_state:
        st.session_state.api_configured = False
    if 'wc_api' not in st.session_state:
        st.session_state.wc_api = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
    if 'products_data' not in st.session_state:
        st.session_state.products_data = None
    if 'subscriptions_data' not in st.session_state:
        st.session_state.subscriptions_data = None
    if 'customers_data' not in st.session_state:
        st.session_state.customers_data = None
    if 'all_users_data' not in st.session_state:
        st.session_state.all_users_data = None

def sidebar_config():
    """Sidebar configuration"""
    st.sidebar.markdown("""
    <div class="sidebar-logo">
        <h2>🏠 AI PropIQ</h2>
        <p>Real Estate Intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # User info
    if st.session_state.authenticated and st.session_state.user_data:
        user = st.session_state.user_data
        
        st.sidebar.markdown(f"""
        <div class="user-card">
            <h4>👤 {user['name']}</h4>
            <p>📧 {user['email']}</p>
            <p>🎭 {user['role'].title()}</p>
            <p>🆔 Customer ID: {user['customer_id']}</p>
            {f'<span class="premium-badge">⭐ Premium Member</span>' if user['subscription_status'] == 'active' else '❌ Free User'}
        </div>
        """, unsafe_allow_html=True)
        
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.rerun()
    
    # API Configuration (only for authenticated users)
    if st.session_state.authenticated:
        st.sidebar.markdown("---")
        st.sidebar.title("🔐 API Configuration")
        
        with st.sidebar.expander("⚙️ WordPress/WooCommerce Settings", expanded=not st.session_state.api_configured):
            with st.form("api_config"):
                base_url = st.text_input(
                    "WordPress/WooCommerce URL",
                    placeholder="https://yoursite.com",
                    help="Your WordPress site URL with WooCommerce"
                )
                
                consumer_key = st.text_input(
                    "WooCommerce Consumer Key",
                    type="password",
                    help="WooCommerce REST API Consumer Key"
                )
                
                consumer_secret = st.text_input(
                    "WooCommerce Consumer Secret",
                    type="password",
                    help="WooCommerce REST API Consumer Secret"
                )
                
                submitted = st.form_submit_button("🔗 Connect to WordPress/WooCommerce")
                
                if submitted and base_url and consumer_key and consumer_secret:
                    st.session_state.wc_api = WordPressWooCommerceAPI(base_url, consumer_key, consumer_secret)
                    
                    with st.spinner("Testing connection to WordPress and WooCommerce..."):
                        result = st.session_state.wc_api.test_connection()
                    
                    if result['success']:
                        st.session_state.api_configured = True
                        st.success("✅ Connected to WordPress and WooCommerce!")
                        st.info(f"WooCommerce: {result['woocommerce_status']}")
                        st.info(f"WordPress: {result['wordpress_status']}")
                    else:
                        st.session_state.api_configured = False
                        st.error(f"❌ Connection Failed: {result['error']}")
        
        # Navigation
        st.sidebar.markdown("---")
        st.sidebar.title("📍 Navigation")
        
        if st.session_state.user_data['subscription_status'] == 'active':
            page_options = ["Dashboard", "Property Analytics", "Market Insights", "User Management", "WooCommerce Sync"]
        else:
            page_options = ["Upgrade Required"]
        
        return st.sidebar.selectbox(
            "Go to:",
            page_options,
            key="nav_select"
        )
    
    return None

def login_page():
    """Display login page with real WordPress authentication"""
    st.markdown('<h1 class="main-header">🏠 AI PropIQ Login</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 WordPress Login")
        st.info("Enter your WordPress username and password to access AI PropIQ")
        
        with st.form("login_form"):
            username = st.text_input("WordPress Username", placeholder="Enter your WordPress username")
            password = st.text_input("Password", type="password", placeholder="Enter your WordPress password")
            
            login_button = st.form_submit_button("🚀 Login with WordPress", use_container_width=True)
            
            if login_button and username and password:
                if not st.session_state.api_configured or not st.session_state.wc_api:
                    st.error("❌ Please configure WordPress/WooCommerce API settings first!")
                    st.info("You need to set up the API connection before logging in.")
                else:
                    with st.spinner("Authenticating with WordPress..."):
                        result = st.session_state.wc_api.authenticate_user(username, password)
                    
                    if result['success']:
                        user_data = result['user']
                        
                        # Check subscription status for product ID 190
                        if user_data['subscription_status'] == 'active' and user_data['subscription_product_id'] == 190:
                            st.session_state.authenticated = True
                            st.session_state.user_data = user_data
                            st.success("✅ Login successful! Welcome to AI PropIQ Premium!")
                            time.sleep(1)
                            st.rerun()
                        elif user_data['role'] == 'administrator':
                            st.session_state.authenticated = True
                            st.session_state.user_data = user_data
                            st.success("✅ Admin login successful! Welcome to AI PropIQ!")
                            time.sleep(1)
                            st.rerun()
                        elif user_data['subscription_status'] == 'inactive':
                            st.error("❌ Your subscription is inactive. Please upgrade to access AI PropIQ.")
                            st.markdown("**[🔗 Upgrade to Premium - aipropiq.com](https://aipropiq.com)**")
                        else:
                            st.error("❌ Premium subscription required. Product ID 190 subscription not found.")
                            st.markdown("**[🔗 Get Premium Access - aipropiq.com](https://aipropiq.com)**")
                    else:
                        st.error(f"❌ Login failed: {result['error']}")
        
        # API Configuration shortcut
        st.markdown("---")
        st.markdown("### ⚙️ First Time Setup")
        st.info("Need to configure WordPress/WooCommerce connection? Set it up in the sidebar after logging in as an admin, or contact your administrator.")
        
        st.markdown('</div>', unsafe_allow_html=True)

def dashboard_page():
    """Main dashboard page"""
    st.markdown('<h1 class="main-header">🏠 AI PropIQ Dashboard</h1>', unsafe_allow_html=True)
    
    # Show user welcome message
    if st.session_state.user_data:
        user = st.session_state.user_data
        st.success(f"Welcome back, {user['name']}! You have {user['role']} access with {'active' if user['subscription_status'] == 'active' else 'inactive'} subscription.")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🏠 Properties</h3>
            <h2>2,847</h2>
            <p>+12% this month</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>💰 Avg Price</h3>
            <h2>$485,000</h2>
            <p>+3.2% this month</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>📈 Market Trend</h3>
            <h2>Bullish</h2>
            <p>Strong demand</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>⏱️ Days on Market</h3>
            <h2>23</h2>
            <p>-5 days vs last month</p>
        </div>
        """, unsafe_allow_html=True)
    
    # WordPress/WooCommerce Integration Status
    if st.session_state.api_configured:
        st.success("✅ WordPress/WooCommerce Integration: Connected")
    else:
        st.warning("⚠️ WordPress/WooCommerce Integration: Not configured")
    
    # Recent Activity
    st.markdown('<h2 class="section-header">📊 Recent Market Activity</h2>', unsafe_allow_html=True)
    
    # Sample data
    recent_sales = pd.DataFrame({
        'Property': ['123 Main St', '456 Oak Ave', '789 Pine Rd', '321 Elm St', '654 Maple Dr'],
        'Price': ['$520,000', '$385,000', '$675,000', '$445,000', '$590,000'],
        'Bedrooms': [3, 2, 4, 3, 3],
        'Bathrooms': [2, 1.5, 3, 2.5, 2],
        'Sq Ft': ['1,850', '1,200', '2,400', '1,650', '1,900'],
        'Sale Date': ['2024-08-15', '2024-08-14', '2024-08-13', '2024-08-12', '2024-08-11']
    })
    
    st.dataframe(recent_sales, use_container_width=True)
    
    # Market insights
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="section-header">🎯 Market Insights</h3>', unsafe_allow_html=True)
        st.info("📈 **Housing prices up 3.2%** this month compared to last month")
        st.success("🏠 **Inventory increased by 8%** - More options for buyers")
        st.warning("⚡ **Fast-moving market** - Average time on market decreased")
        
    with col2:
        st.markdown('<h3 class="section-header">🔥 Hot Neighborhoods</h3>', unsafe_allow_html=True)
        hot_areas = pd.DataFrame({
            'Neighborhood': ['Downtown', 'Riverside', 'Hillcrest', 'Oakwood', 'Sunset'],
            'Avg Price': ['$650K', '$480K', '$720K', '$420K', '$580K'],
            'Change': ['+8.5%', '+5.2%', '+12.1%', '+3.8%', '+6.7%']
        })
        st.dataframe(hot_areas, use_container_width=True)

def property_analytics_page():
    """Property analytics page"""
    st.markdown('<h1 class="main-header">🏠 Property Analytics</h1>', unsafe_allow_html=True)
    
    # Property search and analysis
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        address = st.text_input("🔍 Enter Property Address", placeholder="123 Main Street, City, State")
    
    with col2:
        property_type = st.selectbox("Property Type", ["Single Family", "Condo", "Townhouse", "Multi-Family"])
    
    with col3:
        if st.button("🔍 Analyze Property", use_container_width=True):
            if address:
                st.success(f"Analyzing: {address}")
    
    # Property details and analysis
    if address:
        st.markdown('<h2 class="section-header">📊 Property Analysis Report</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏠 Property Details")
            st.write("**Address:** 123 Main Street")
            st.write("**Type:** Single Family Home")
            st.write("**Built:** 1995")
            st.write("**Bedrooms:** 3")
            st.write("**Bathrooms:** 2.5")
            st.write("**Square Feet:** 1,850")
            st.write("**Lot Size:** 0.25 acres")
            
            st.markdown("### 💰 Valuation")
            st.metric("Estimated Value", "$485,000", "+$15,000")
            st.metric("Price per Sq Ft", "$262", "+$8")
            
        with col2:
            st.markdown("### 📈 Market Analysis")
            
            # Sample chart data
            dates = pd.date_range('2024-01-01', periods=8, freq='M')
            values = [450000, 455000, 462000, 468000, 475000, 480000, 485000, 485000]
            
            chart_data = pd.DataFrame({
                'Date': dates,
                'Value': values
            })
            
            st.line_chart(chart_data.set_index('Date'))
            
            st.markdown("### 🎯 Investment Insights")
            st.success("✅ **Good Investment** - Property value trending upward")
            st.info("📊 **Market Position** - Priced competitively for area")
            st.warning("⚠️ **Consider** - Property taxes increased 2% this year")
    
    # Comparable properties
    st.markdown('<h2 class="section-header">🔄 Comparable Properties</h2>', unsafe_allow_html=True)
    
    comps_data = pd.DataFrame({
        'Address': ['456 Oak Street', '789 Pine Avenue', '321 Elm Road', '654 Maple Drive'],
        'Distance': ['0.2 miles', '0.3 miles', '0.4 miles', '0.5 miles'],
        'Price': ['$475,000', '$495,000', '$465,000', '$510,000'],
        'Bedrooms': [3, 3, 2, 4],
        'Bathrooms': [2, 3, 2, 3],
        'Sq Ft': ['1,800', '1,900', '1,650', '2,100'],
        'Sale Date': ['2024-07-15', '2024-06-28', '2024-08-02', '2024-05-20']
    })
    
    st.dataframe(comps_data, use_container_width=True)

def market_insights_page():
    """Market insights page"""
    st.markdown('<h1 class="main-header">📊 Market Insights</h1>', unsafe_allow_html=True)
    
    # Market overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Market Temperature", "Hot", "🔥")
    with col2:
        st.metric("Inventory Level", "Low", "📉")
    with col3:
        st.metric("Price Trend", "Rising", "📈")
    with col4:
        st.metric("Buyer Demand", "High", "🎯")
    
    # Market trends
    st.markdown('<h2 class="section-header">📈 Market Trends</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 Median Home Prices")
        
        # Sample price trend data
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']
        prices = [450000, 455000, 462000, 468000, 475000, 480000, 485000, 490000]
        
        price_data = pd.DataFrame({
            'Month': months,
            'Price': prices
        })
        
        st.line_chart(price_data.set_index('Month'))
        
    with col2:
        st.markdown("### 📊 Market Activity")
        
        activity_data = pd.DataFrame({
            'Metric': ['New Listings', 'Pending Sales', 'Closed Sales', 'Days on Market'],
            'This Month': [245, 189, 167, 23],
            'Last Month': [220, 175, 155, 28],
            'Change': ['+11%', '+8%', '+8%', '-18%']
        })
        
        st.dataframe(activity_data, use_container_width=True)

def user_management_page():
    """Enhanced user management page with real WordPress/WooCommerce data"""
    st.markdown('<h1 class="main-header">👥 User Management</h1>', unsafe_allow_html=True)
    
    # Check if user is admin
    if st.session_state.user_data['role'] != 'administrator':
        st.error("🚫 Access Denied: Admin privileges required")
        return
    
    if not st.session_state.api_configured:
        st.warning("⚠️ Please configure WordPress/WooCommerce API first")
        return
    
    # Sync users button
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Sync All Users from WordPress/WooCommerce", use_container_width=True):
            with st.spinner("Syncing users and subscriptions..."):
                result = st.session_state.wc_api.get_all_users_with_subscriptions()
                st.session_state.all_users_data = result
            
            if result['success']:
                st.success(f"✅ Synced {len(result['data'])} users with subscription data!")
            else:
                st.error(f"❌ Sync failed: {result['error']}")
    
    with col2:
        if st.button("📊 Refresh Data", use_container_width=True):
            st.session_state.all_users_data = None
            st.rerun()
    
    with col3:
        last_sync = datetime.now().strftime('%H:%M:%S')
        st.info(f"🕒 Last Sync: {last_sync}")
    
    # Display user data if available
    if st.session_state.all_users_data and st.session_state.all_users_data['success']:
        users_data = st.session_state.all_users_data['data']
        
        # Calculate statistics
        total_users = len(users_data)
        active_subscribers = sum(1 for user in users_data if user['role'] == 'subscriber')
        inactive_users = sum(1 for user in users_data if user['role'] == 'customer')
        
        # User stats overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Users", total_users)
        with col2:
            st.metric("Active Subscribers (ID 190)", active_subscribers)
        with col3:
            st.metric("Regular Customers", inactive_users)
        with col4:
            st.metric("Admin Users", 1)  # At least current admin
        
        # User management tabs
        tab1, tab2, tab3 = st.tabs(["👥 All Users", "⭐ Product 190 Subscribers", "📊 Analytics"])
        
        with tab1:
            st.markdown('<h3 class="section-header">All WordPress/WooCommerce Users</h3>', unsafe_allow_html=True)
            
            # Convert users to DataFrame
            users_list = []
            for user in users_data:
                subscription_info = "None"
                if user['subscriptions']:
                    active_subs = [sub for sub in user['subscriptions'] if sub['status'] == 'active']
                    if active_subs:
                        subscription_info = f"Active ({len(active_subs)} subs)"
                    else:
                        subscription_info = f"Inactive ({len(user['subscriptions'])} subs)"
                
                users_list.append({
                    'ID': user['id'],
                    'Name': f"{user['first_name']} {user['last_name']}".strip() or 'N/A',
                    'Email': user['email'],
                    'Username': user['username'] or 'N/A',
                    'Role': user['role'].title(),
                    'Status': '✅ Premium' if user['role'] == 'subscriber' else '👤 Customer',
                    'Subscriptions': subscription_info,
                    'Orders': user['orders_count'],
                    'Total Spent': f"${float(user['total_spent']):.2f}",
                    'Date Created': user['date_created'][:10] if user['date_created'] else 'N/A'
                })
            
            users_df = pd.DataFrame(users_list)
            st.dataframe(users_df, use_container_width=True)
        
        with tab2:
            st.markdown('<h3 class="section-header">Product 190 Premium Subscribers</h3>', unsafe_allow_html=True)
            
            # Filter users with active Product 190 subscriptions
            premium_users = []
            for user in users_data:
                for subscription in user['subscriptions']:
                    if subscription['product_id'] == 190 and subscription['status'] == 'active':
                        premium_users.append({
                            'ID': user['id'],
                            'Name': f"{user['first_name']} {user['last_name']}".strip() or 'N/A',
                            'Email': user['email'],
                            'Username': user['username'] or 'N/A',
                            'Subscription ID': subscription['id'],
                            'Status': subscription['status'].title(),
                            'Monthly Total': f"${float(subscription['total']):.2f}",
                            'Start Date': subscription['start_date'][:10] if subscription['start_date'] else 'N/A',
                            'Next Payment': subscription['next_payment'][:10] if subscription['next_payment'] else 'N/A',
                            'Billing Period': f"{subscription.get('billing_interval', 1)} {subscription.get('billing_period', 'month')}(s)"
                        })
                        break  # Only add once per user
            
            if premium_users:
                premium_df = pd.DataFrame(premium_users)
                st.dataframe(premium_df, use_container_width=True)
            else:
                st.info("No active Product 190 subscribers found.")
        
        with tab3:
            st.markdown('<h3 class="section-header">User & Subscription Analytics</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 💰 Revenue Analysis")
                
                # Calculate revenue metrics
                total_revenue = sum(float(user['total_spent']) for user in users_data)
                monthly_recurring = 0
                
                for user in users_data:
                    for sub in user['subscriptions']:
                        if sub['status'] == 'active' and sub['product_id'] == 190:
                            monthly_recurring += float(sub['total'])
                
                st.metric("Total Customer Revenue", f"${total_revenue:,.2f}")
                st.metric("Monthly Recurring Revenue", f"${monthly_recurring:,.2f}")
                st.metric("Average Revenue Per User", f"${total_revenue/max(total_users, 1):,.2f}")
            
            with col2:
                st.markdown("### 📈 User Engagement")
                
                # User activity metrics
                users_with_orders = sum(1 for user in users_data if user['orders_count'] > 0)
                avg_orders = sum(user['orders_count'] for user in users_data) / max(total_users, 1)
                
                engagement_data = pd.DataFrame({
                    'Metric': [
                        'Users with Orders', 
                        'Average Orders per User',
                        'Conversion Rate',
                        'Premium Subscription Rate'
                    ],
                    'Value': [
                        f"{users_with_orders}",
                        f"{avg_orders:.1f}",
                        f"{(active_subscribers/max(inactive_users, 1))*100:.1f}%",
                        f"{(active_subscribers/max(total_users, 1))*100:.1f}%"
                    ]
                })
                st.dataframe(engagement_data, use_container_width=True)
    
    elif st.session_state.all_users_data and not st.session_state.all_users_data['success']:
        st.error(f"❌ Failed to load user data: {st.session_state.all_users_data['error']}")
    else:
        st.info("👆 Click 'Sync All Users' to load WordPress/WooCommerce user data")

def woocommerce_sync_page():
    """WooCommerce synchronization and testing page"""
    st.markdown('<h1 class="main-header">🔄 WordPress/WooCommerce Sync</h1>', unsafe_allow_html=True)
    
    if not st.session_state.api_configured:
        st.warning("⚠️ Please configure your WordPress/WooCommerce API credentials in the sidebar first.")
        return
    
    # Connection status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Test Connection", use_container_width=True):
            with st.spinner("Testing WordPress/WooCommerce connection..."):
                result = st.session_state.wc_api.test_connection()
            if result['success']:
                st.success("✅ Connection successful!")
                st.info(f"WooCommerce: {result['woocommerce_status']}")
                st.info(f"WordPress: {result['wordpress_status']}")
            else:
                st.error(f"❌ Connection failed: {result['error']}")
    
    with col2:
        st.info(f"🌐 API Status: {'🟢 Connected' if st.session_state.api_configured else '🔴 Disconnected'}")
    
    with col3:
        st.info(f"🕒 Last Check: {datetime.now().strftime('%H:%M:%S')}")
    
    # Tabs for different data types
    tab1, tab2, tab3 = st.tabs(["📦 Products", "🔄 Subscriptions", "👥 Customers"])
    
    with tab1:
        st.markdown("### 📦 WordPress/WooCommerce Products")
        
        if st.button("🔄 Load Products"):
            with st.spinner("Loading products from WooCommerce..."):
                result = st.session_state.wc_api.get_products(per_page=20)
                st.session_state.products_data = result
        
        if st.session_state.products_data and st.session_state.products_data['success']:
            products = st.session_state.products_data['data']
            
            if products:
                products_df = pd.DataFrame([
                    {
                        'ID': p['id'],
                        'Name': p['name'][:50] + '...' if len(p['name']) > 50 else p['name'],
                        'Type': p['type'],
                        'Status': p['status'],
                        'Price': f"${p['price']}" if p['price'] else 'Free',
                        'AI PropIQ Product': '🎯 YES' if p['id'] == 190 else 'No'
                    }
                    for p in products
                ])
                
                st.dataframe(products_df, use_container_width=True)
            else:
                st.info("No products found.")
    
    with tab2:
        st.markdown("### 🔄 Product 190 Subscriptions")
        
        if st.button("🔄 Load Subscriptions"):
            with st.spinner("Loading subscriptions from WooCommerce..."):
                result = st.session_state.wc_api.get_subscriptions(per_page=20, product_id=190)
                st.session_state.subscriptions_data = result
        
        if st.session_state.subscriptions_data and st.session_state.subscriptions_data['success']:
            subscriptions = st.session_state.subscriptions_data['data']
            
            if subscriptions:
                st.success(f"Found {len(subscriptions)} subscriptions for Product ID 190")
                
                subs_df = pd.DataFrame([
                    {
                        'Subscription ID': s['id'],
                        'Status': s['status'],
                        'Customer': f"{s['billing']['first_name']} {s['billing']['last_name']}",
                        'Email': s['billing']['email'],
                        'Total': f"${s['total']}",
                        'Start Date': s['date_created'][:10],
                        'Next Payment': s.get('next_payment_date', 'N/A')[:10] if s.get('next_payment_date') else 'N/A'
                    }
                    for s in subscriptions
                ])
                st.dataframe(subs_df, use_container_width=True)
            else:
                st.warning("No subscriptions found for Product ID 190")
    
    with tab3:
        st.markdown("### 👥 WooCommerce Customers")
        
        if st.button("🔄 Load Customers"):
            with st.spinner("Loading customers from WooCommerce..."):
                result = st.session_state.wc_api.get_customers(per_page=20)
                st.session_state.customers_data = result
        
        if st.session_state.customers_data and st.session_state.customers_data['success']:
            customers = st.session_state.customers_data['data']
            
            if customers:
                customers_df = pd.DataFrame([
                    {
                        'Customer ID': c['id'],
                        'Name': f"{c['first_name']} {c['last_name']}",
                        'Email': c['email'],
                        'Username': c.get('username', 'N/A'),
                        'Orders': c['orders_count'],
                        'Total Spent': f"${c['total_spent']}",
                        'Date Created': c['date_created'][:10]
                    }
                    for c in customers
                ])
                st.dataframe(customers_df, use_container_width=True)
            else:
                st.info("No customers found.")

def upgrade_required_page():
    """Display upgrade required page"""
    st.markdown('<h1 class="main-header">🔒 Premium Access Required</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin: 2rem 0;">
            <h2>🚀 Unlock Full Access</h2>
            <p>You need an active subscription to Product ID 190 to access AI PropIQ's advanced features.</p>
            <h3>✨ Premium Features:</h3>
            <ul style="text-align: left; max-width: 300px; margin: 0 auto;">
                <li>🏠 Advanced Property Analytics</li>
                <li>📊 Real-time Market Insights</li>
                <li>👥 User Management Dashboard</li>
                <li>📈 Investment Analysis Tools</li>
                <li>🔔 Price Alert Notifications</li>
                <li>🔄 WordPress/WooCommerce Integration</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; margin: 2rem 0;">
            <a href="https://aipropiq.com" target="_blank" style="background: linear-gradient(45deg, #FFD700, #FFA500); color: black; padding: 15px 30px; border-radius: 25px; text-decoration: none; font-weight: bold; font-size: 1.2rem;">
                🌟 Subscribe to Product ID 190 - Visit aipropiq.com
            </a>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main application function"""
    init_session_state()
    
    # Show login page if not authenticated
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Configure sidebar and get selected page
    selected_page = sidebar_config()
    
    # Route to appropriate page
    if selected_page == "Dashboard":
        dashboard_page()
    elif selected_page == "Property Analytics":
        property_analytics_page()
    elif selected_page == "Market Insights":
        market_insights_page()
    elif selected_page == "User Management":
        user_management_page()
    elif selected_page == "WooCommerce Sync":
        woocommerce_sync_page()
    elif selected_page == "Upgrade Required":
        upgrade_required_page()
    else:
        dashboard_page()

if __name__ == "__main__":
    main()
