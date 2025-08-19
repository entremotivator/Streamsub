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

# Demo users data
DEMO_USERS = {
    "admin": {
        "password": "admin123",
        "email": "admin@aipropiq.com",
        "role": "administrator",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "Admin User",
        "customer_id": 1
    },
    "john_doe": {
        "password": "john123",
        "email": "john@example.com",
        "role": "subscriber",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "John Doe",
        "customer_id": 2
    },
    "jane_smith": {
        "password": "jane123",
        "email": "jane@example.com",
        "role": "subscriber",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "Jane Smith",
        "customer_id": 3
    },
    "mike_wilson": {
        "password": "mike123",
        "email": "mike@example.com",
        "role": "subscriber",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "Mike Wilson",
        "customer_id": 4
    },
    "sarah_connor": {
        "password": "sarah123",
        "email": "sarah@example.com",
        "role": "subscriber",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "Sarah Connor",
        "customer_id": 5
    },
    "bob_builder": {
        "password": "bob123",
        "email": "bob@example.com",
        "role": "customer",
        "subscription_status": "inactive",
        "subscription_product_id": None,
        "name": "Bob Builder",
        "customer_id": 6
    },
    "alice_wonder": {
        "password": "alice123",
        "email": "alice@example.com",
        "role": "subscriber",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "Alice Wonder",
        "customer_id": 7
    },
    "charlie_brown": {
        "password": "charlie123",
        "email": "charlie@example.com",
        "role": "customer",
        "subscription_status": "inactive",
        "subscription_product_id": None,
        "name": "Charlie Brown",
        "customer_id": 8
    },
    "diana_prince": {
        "password": "diana123",
        "email": "diana@example.com",
        "role": "subscriber",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "Diana Prince",
        "customer_id": 9
    },
    "peter_parker": {
        "password": "peter123",
        "email": "peter@example.com",
        "role": "subscriber",
        "subscription_status": "active",
        "subscription_product_id": 190,
        "name": "Peter Parker",
        "customer_id": 10
    }
}

class WooCommerceAPI:
    def __init__(self, base_url: str, consumer_key: str, consumer_secret: str):
        self.base_url = base_url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth = (consumer_key, consumer_secret)
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """Authenticate user with WordPress/WooCommerce"""
        try:
            # For demo purposes, check against demo users first
            if username in DEMO_USERS:
                demo_user = DEMO_USERS[username]
                if demo_user["password"] == password:
                    return {
                        'success': True,
                        'user': demo_user,
                        'message': 'Authentication successful'
                    }
            
            # In production, this would connect to WordPress authentication
            # url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
            # payload = {"username": username, "password": password}
            # response = requests.post(url, json=payload)
            
            return {'success': False, 'error': 'Invalid credentials'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_subscription_status(self, customer_id: int, product_id: int = 190) -> Dict:
        """Check if user has active subscription for specific product"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/subscriptions"
            params = {
                'customer': customer_id,
                'status': 'active',
                'per_page': 100
            }
            response = requests.get(url, auth=self.auth, params=params)
            
            if response.status_code == 200:
                subscriptions = response.json()
                
                # Check if any subscription contains the product
                for subscription in subscriptions:
                    for item in subscription.get('line_items', []):
                        if item.get('product_id') == product_id:
                            return {
                                'success': True,
                                'has_subscription': True,
                                'subscription': subscription,
                                'product_id': product_id
                            }
                
                return {'success': True, 'has_subscription': False}
            else:
                return {'success': False, 'error': 'Failed to check subscription'}
                
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
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json(),
                'total_pages': int(response.headers.get('X-WP-TotalPages', 1)),
                'total_items': int(response.headers.get('X-WP-Total', 0))
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_subscriptions(self, per_page: int = 10, page: int = 1) -> Dict:
        """Fetch subscriptions from WooCommerce"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/subscriptions"
            params = {
                'per_page': per_page,
                'page': page
            }
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json(),
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
            response = requests.get(url, auth=self.auth, params=params)
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
            url = f"{self.base_url}/wp-json/wc/v3/system_status"
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            return {'success': True, 'message': 'Connection successful!'}
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
        
        with st.sidebar.expander("⚙️ WooCommerce Settings", expanded=False):
            with st.form("api_config"):
                base_url = st.text_input(
                    "Store URL",
                    placeholder="https://yourstore.com",
                    help="Your WooCommerce store URL"
                )
                
                consumer_key = st.text_input(
                    "Consumer Key",
                    type="password",
                    help="WooCommerce REST API Consumer Key"
                )
                
                consumer_secret = st.text_input(
                    "Consumer Secret",
                    type="password",
                    help="WooCommerce REST API Consumer Secret"
                )
                
                submitted = st.form_submit_button("Connect")
                
                if submitted and base_url and consumer_key and consumer_secret:
                    st.session_state.wc_api = WooCommerceAPI(base_url, consumer_key, consumer_secret)
                    
                    with st.spinner("Testing connection..."):
                        result = st.session_state.wc_api.test_connection()
                    
                    if result['success']:
                        st.session_state.api_configured = True
                        st.success("✅ Connected!")
                    else:
                        st.session_state.api_configured = False
                        st.error(f"❌ Failed: {result['error']}")
        
        # Navigation
        st.sidebar.markdown("---")
        st.sidebar.title("📍 Navigation")
        
        if st.session_state.user_data['subscription_status'] == 'active':
            page_options = ["Dashboard", "Property Analytics", "Market Insights", "User Management"]
        else:
            page_options = ["Upgrade Required"]
        
        return st.sidebar.selectbox(
            "Go to:",
            page_options,
            key="nav_select"
        )
    
    return None

def login_page():
    """Display login page"""
    st.markdown('<h1 class="main-header">🏠 AI PropIQ Login</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Member Login")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            with col1:
                login_button = st.form_submit_button("🚀 Login", use_container_width=True)
            with col2:
                demo_button = st.form_submit_button("👀 Demo Users", use_container_width=True)
            
            if login_button and username and password:
                # Create temporary API instance for authentication
                temp_api = WooCommerceAPI("https://demo.com", "demo", "demo")
                result = temp_api.authenticate_user(username, password)
                
                if result['success']:
                    user_data = result['user']
                    
                    # Check subscription status
                    if user_data['subscription_status'] == 'active' and user_data['subscription_product_id'] == 190:
                        st.session_state.authenticated = True
                        st.session_state.user_data = user_data
                        st.success("✅ Login successful! Welcome to AI PropIQ!")
                        time.sleep(1)
                        st.rerun()
                    elif user_data['subscription_status'] == 'inactive':
                        st.error("❌ Your subscription is inactive. Redirecting to upgrade page...")
                        st.markdown("**[🔗 Upgrade to Premium - aipropiq.com](https://aipropiq.com)**")
                    else:
                        st.error("❌ Premium subscription required for access.")
                        st.markdown("**[🔗 Get Premium Access - aipropiq.com](https://aipropiq.com)**")
                else:
                    st.error("❌ Invalid username or password")
            
            if demo_button:
                st.info("📋 **Demo Users Available:**")
                
                # Show paid users
                st.markdown("**💎 Premium Users (Access Granted):**")
                paid_users = [k for k, v in DEMO_USERS.items() if v['subscription_status'] == 'active']
                for user in paid_users[:5]:  # Show first 5
                    user_data = DEMO_USERS[user]
                    st.markdown(f"• **{user}** / {user_data['password']} - {user_data['name']} ⭐")
                
                # Show unpaid users
                st.markdown("**🆓 Free Users (Redirect to aipropiq.com):**")
                unpaid_users = [k for k, v in DEMO_USERS.items() if v['subscription_status'] == 'inactive']
                for user in unpaid_users:
                    user_data = DEMO_USERS[user]
                    st.markdown(f"• **{user}** / {user_data['password']} - {user_data['name']} ❌")
        
        st.markdown('</div>', unsafe_allow_html=True)

def upgrade_required_page():
    """Display upgrade required page"""
    st.markdown('<h1 class="main-header">🔒 Premium Access Required</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin: 2rem 0;">
            <h2>🚀 Unlock Full Access</h2>
            <p>Get premium access to AI PropIQ's advanced real estate analytics and insights.</p>
            <h3>✨ Premium Features:</h3>
            <ul style="text-align: left; max-width: 300px; margin: 0 auto;">
                <li>🏠 Advanced Property Analytics</li>
                <li>📊 Real-time Market Insights</li>
                <li>👥 User Management Dashboard</li>
                <li>📈 Investment Analysis Tools</li>
                <li>🔔 Price Alert Notifications</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; margin: 2rem 0;">
            <a href="https://aipropiq.com" target="_blank" style="background: linear-gradient(45deg, #FFD700, #FFA500); color: black; padding: 15px 30px; border-radius: 25px; text-decoration: none; font-weight: bold; font-size: 1.2rem;">
                🌟 Upgrade to Premium - Visit aipropiq.com
            </a>
        </div>
        """, unsafe_allow_html=True)

def dashboard_page():
    """Main dashboard page"""
    st.markdown('<h1 class="main-header">🏠 AI PropIQ Dashboard</h1>', unsafe_allow_html=True)
    
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
            import numpy as np
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
        prices = [420000, 425000, 435000, 445000, 455000, 465000, 475000, 485000]
        
        price_data = pd.DataFrame({
            'Month': months,
            'Median Price': prices
        })
        
        st.line_chart(price_data.set_index('Month'))
    
    with col2:
        st.markdown("### 🏠 Inventory Levels")
        
        inventory = [1200, 1150, 1100, 1050, 980, 920, 850, 800]
        
        inventory_data = pd.DataFrame({
            'Month': months,
            'Available Homes': inventory
        })
        
        st.line_chart(inventory_data.set_index('Month'))
    
    # Regional analysis
    st.markdown('<h2 class="section-header">🗺️ Regional Market Analysis</h2>', unsafe_allow_html=True)
    
    regional_data = pd.DataFrame({
        'Region': ['Downtown', 'Suburbs North', 'Suburbs South', 'Waterfront', 'Historic District'],
        'Avg Price': ['$650,000', '$485,000', '$425,000', '$850,000', '$720,000'],
        'Price Change (1Y)': ['+12.5%', '+8.2%', '+6.8%', '+15.3%', '+10.1%'],
        'Inventory': ['Low', 'Moderate', 'High', 'Very Low', 'Low'],
        'Days on Market': [18, 25, 32, 12, 22],
        'Market Status': ['🔥 Hot', '📈 Rising', '📊 Stable', '🚀 Explosive', '🔥 Hot']
    })
    
    st.dataframe(regional_data, use_container_width=True)
    
    # Market predictions
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="section-header">🔮 Market Predictions</h3>', unsafe_allow_html=True)
        st.info("📊 **Next 3 Months:** Prices expected to rise 2-4%")
        st.success("🏠 **Inventory:** Slight increase expected in fall")
        st.warning("📈 **Interest Rates:** May impact buyer demand")
        st.error("⚠️ **Risk Factor:** Economic uncertainty ahead")
    
    with col2:
        st.markdown('<h3 class="section-header">💡 Investment Opportunities</h3>', unsafe_allow_html=True)
        opportunities = pd.DataFrame({
            'Opportunity': ['Fix & Flip', 'Buy & Hold', 'Commercial', 'New Development'],
            'ROI Potential': ['15-25%', '8-12%', '10-18%', '20-30%'],
            'Risk Level': ['High', 'Medium', 'Medium', 'High'],
            'Timeline': ['6-12 months', '5-10 years', '3-7 years', '2-5 years']
        })
        st.dataframe(opportunities, use_container_width=True)

def user_management_page():
    """User management page for admin users"""
    st.markdown('<h1 class="main-header">👥 User Management</h1>', unsafe_allow_html=True)
    
    # Check if user is admin
    if st.session_state.user_data['role'] != 'administrator':
        st.error("🚫 Access Denied: Admin privileges required")
        return
    
    # User stats overview
    col1, col2, col3, col4 = st.columns(4)
    
    active_users = sum(1 for user in DEMO_USERS.values() if user['subscription_status'] == 'active')
    inactive_users = sum(1 for user in DEMO_USERS.values() if user['subscription_status'] == 'inactive')
    
    with col1:
        st.metric("Total Users", len(DEMO_USERS))
    with col2:
        st.metric("Active Subscribers", active_users)
    with col3:
        st.metric("Free Users", inactive_users)
    with col4:
        st.metric("Admin Users", 1)
    
    # User management tabs
    tab1, tab2, tab3 = st.tabs(["👥 All Users", "⭐ Subscribers", "📊 Analytics"])
    
    with tab1:
        st.markdown('<h3 class="section-header">All Users</h3>', unsafe_allow_html=True)
        
        # Convert demo users to DataFrame
        users_list = []
        for username, data in DEMO_USERS.items():
            users_list.append({
                'Username': username,
                'Name': data['name'],
                'Email': data['email'],
                'Role': data['role'].title(),
                'Status': '✅ Active' if data['subscription_status'] == 'active' else '❌ Inactive',
                'Product ID': data.get('subscription_product_id', 'N/A'),
                'Customer ID': data['customer_id']
            })
        
        users_df = pd.DataFrame(users_list)
        st.dataframe(users_df, use_container_width=True)
        
        # User actions
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📧 Send Newsletter", use_container_width=True):
                st.success("Newsletter sent to all users!")
        with col2:
            if st.button("📊 Export Users", use_container_width=True):
                st.success("User data exported successfully!")
        with col3:
            if st.button("🔄 Sync with WordPress", use_container_width=True):
                st.success("User data synchronized!")
    
    with tab2:
        st.markdown('<h3 class="section-header">Premium Subscribers</h3>', unsafe_allow_html=True)
        
        # Filter active subscribers
        active_subscribers = [
            {
                'Username': username,
                'Name': data['name'],
                'Email': data['email'],
                'Product ID': data['subscription_product_id'],
                'Customer ID': data['customer_id'],
                'Join Date': '2024-08-01'  # Sample date
            }
            for username, data in DEMO_USERS.items() 
            if data['subscription_status'] == 'active'
        ]
        
        subscribers_df = pd.DataFrame(active_subscribers)
        st.dataframe(subscribers_df, use_container_width=True)
        
        # Subscription analytics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Subscription Trends")
            # Sample subscription data
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']
            new_subs = [5, 8, 12, 15, 18, 22, 25, 28]
            
            sub_data = pd.DataFrame({
                'Month': months,
                'New Subscribers': new_subs
            })
            
            st.line_chart(sub_data.set_index('Month'))
        
        with col2:
            st.markdown("### 💰 Revenue Overview")
            st.metric("Monthly Recurring Revenue", "$2,980", "+$450")
            st.metric("Average Revenue Per User", "$97", "+$5")
            st.metric("Churn Rate", "3.2%", "-0.8%")
    
    with tab3:
        st.markdown('<h3 class="section-header">User Analytics</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 User Engagement")
            engagement_data = pd.DataFrame({
                'Metric': ['Daily Active Users', 'Weekly Active Users', 'Monthly Active Users', 'Session Duration'],
                'Value': ['45', '68', '89', '12 min'],
                'Change': ['+15%', '+22%', '+18%', '+2 min']
            })
            st.dataframe(engagement_data, use_container_width=True)
        
        with col2:
            st.markdown("### 📱 Platform Usage")
            platform_data = pd.DataFrame({
                'Platform': ['Web Dashboard', 'Mobile App', 'API Access', 'Email Reports'],
                'Users': [75, 45, 12, 89],
                'Percentage': ['84%', '51%', '13%', '100%']
            })
            st.dataframe(platform_data, use_container_width=True)
        
        # Feature usage
        st.markdown("### 🛠️ Feature Usage Analysis")
        feature_usage = pd.DataFrame({
            'Feature': ['Property Analytics', 'Market Insights', 'Price Alerts', 'Comparables', 'Reports'],
            'Usage Count': [1250, 980, 650, 880, 420],
            'User Adoption': ['89%', '78%', '52%', '71%', '34%']
        })
        st.dataframe(feature_usage, use_container_width=True)

def woocommerce_integration_page():
    """WooCommerce integration and testing page"""
    st.markdown('<h1 class="main-header">🛒 WooCommerce Integration</h1>', unsafe_allow_html=True)
    
    if not st.session_state.api_configured:
        st.warning("⚠️ Please configure your WooCommerce API credentials in the sidebar first.")
        return
    
    # Connection status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Test Connection"):
            with st.spinner("Testing connection..."):
                result = st.session_state.wc_api.test_connection()
            if result['success']:
                st.success("✅ Connection successful!")
            else:
                st.error(f"❌ Connection failed: {result['error']}")
    
    with col2:
        st.info(f"🌐 API Status: {'🟢 Connected' if st.session_state.api_configured else '🔴 Disconnected'}")
    
    with col3:
        st.info(f"🕒 Last Check: {datetime.now().strftime('%H:%M:%S')}")
    
    # Tabs for different WooCommerce data
    tab1, tab2, tab3, tab4 = st.tabs(["📦 Products", "🔄 Subscriptions", "👥 Customers", "🧪 API Testing"])
    
    with tab1:
        st.markdown("### 📦 WooCommerce Products")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            per_page = st.selectbox("Items per page:", [10, 20, 50], index=0, key="products_per_page")
        with col2:
            page = st.number_input("Page:", min_value=1, value=1, key="products_page")
        with col3:
            if st.button("🔄 Refresh", key="refresh_products"):
                st.session_state.products_data = None
        
        if st.session_state.products_data is None:
            with st.spinner("Loading products..."):
                result = st.session_state.wc_api.get_products(per_page=per_page, page=page)
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
                        'Stock': p.get('stock_quantity', 'N/A')
                    }
                    for p in products
                ])
                st.dataframe(products_df, use_container_width=True)
            else:
                st.info("No products found.")
        elif st.session_state.products_data:
            st.error(f"Error loading products: {st.session_state.products_data['error']}")
    
    with tab2:
        st.markdown("### 🔄 WooCommerce Subscriptions")
        
        # Focus on product ID 190
        st.info("🎯 Focusing on Product ID 190 - AI PropIQ Premium Subscription")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            per_page = st.selectbox("Items per page:", [10, 20, 50], index=0, key="subs_per_page")
        with col2:
            page = st.number_input("Page:", min_value=1, value=1, key="subs_page")
        with col3:
            if st.button("🔄 Refresh", key="refresh_subs"):
                st.session_state.subscriptions_data = None
        
        if st.session_state.subscriptions_data is None:
            with st.spinner("Loading subscriptions..."):
                result = st.session_state.wc_api.get_subscriptions(per_page=per_page, page=page)
                st.session_state.subscriptions_data = result
        
        if st.session_state.subscriptions_data and st.session_state.subscriptions_data['success']:
            subscriptions = st.session_state.subscriptions_data['data']
            
            if subscriptions:
                # Filter for product ID 190
                product_190_subs = []
                for sub in subscriptions:
                    for item in sub.get('line_items', []):
                        if item.get('product_id') == 190:
                            product_190_subs.append(sub)
                            break
                
                if product_190_subs:
                    st.success(f"Found {len(product_190_subs)} subscriptions for Product ID 190")
                    
                    subs_df = pd.DataFrame([
                        {
                            'ID': s['id'],
                            'Status': s['status'],
                            'Customer': f"{s['billing']['first_name']} {s['billing']['last_name']}",
                            'Email': s['billing']['email'],
                            'Total': f"${s['total']}",
                            'Start Date': s['date_created'][:10]
                        }
                        for s in product_190_subs
                    ])
                    st.dataframe(subs_df, use_container_width=True)
                else:
                    st.warning("No active subscriptions found for Product ID 190")
            else:
                st.info("No subscriptions found.")
        elif st.session_state.subscriptions_data:
            st.error(f"Error loading subscriptions: {st.session_state.subscriptions_data['error']}")
    
    with tab3:
        st.markdown("### 👥 WooCommerce Customers")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            per_page = st.selectbox("Items per page:", [10, 20, 50], index=0, key="customers_per_page")
        with col2:
            page = st.number_input("Page:", min_value=1, value=1, key="customers_page")
        with col3:
            if st.button("🔄 Refresh", key="refresh_customers"):
                st.session_state.customers_data = None
        
        if st.session_state.customers_data is None:
            with st.spinner("Loading customers..."):
                result = st.session_state.wc_api.get_customers(per_page=per_page, page=page)
                st.session_state.customers_data = result
        
        if st.session_state.customers_data and st.session_state.customers_data['success']:
            customers = st.session_state.customers_data['data']
            
            if customers:
                customers_df = pd.DataFrame([
                    {
                        'ID': c['id'],
                        'Name': f"{c['first_name']} {c['last_name']}",
                        'Email': c['email'],
                        'Role': c['role'],
                        'Orders': c['orders_count'],
                        'Total Spent': f"${c['total_spent']}",
                        'Date Created': c['date_created'][:10]
                    }
                    for c in customers
                ])
                st.dataframe(customers_df, use_container_width=True)
            else:
                st.info("No customers found.")
        elif st.session_state.customers_data:
            st.error(f"Error loading customers: {st.session_state.customers_data['error']}")
    
    with tab4:
        st.markdown("### 🧪 API Testing")
        
        with st.form("api_test_form"):
            endpoint = st.text_input(
                "API Endpoint",
                placeholder="products/190",
                help="Enter endpoint relative to /wp-json/wc/v3/"
            )
            
            method = st.selectbox("HTTP Method", ["GET", "POST", "PUT", "DELETE"])
            
            params = st.text_area(
                "Parameters (JSON)",
                placeholder='{"per_page": 10}',
                help="Enter parameters in JSON format"
            )
            
            if st.form_submit_button("🚀 Send Request"):
                if endpoint:
                    try:
                        url = f"{st.session_state.wc_api.base_url}/wp-json/wc/v3/{endpoint}"
                        
                        request_params = {}
                        if params.strip():
                            request_params = json.loads(params)
                        
                        with st.spinner("Sending request..."):
                            if method == "GET":
                                response = requests.get(url, auth=st.session_state.wc_api.auth, params=request_params)
                            elif method == "POST":
                                response = requests.post(url, auth=st.session_state.wc_api.auth, json=request_params)
                            # Add other methods as needed
                        
                        st.write(f"**Status Code:** {response.status_code}")
                        
                        if response.status_code < 400:
                            st.success("✅ Request successful!")
                            try:
                                response_json = response.json()
                                st.json(response_json)
                            except:
                                st.text(response.text)
                        else:
                            st.error("❌ Request failed!")
                            st.text(response.text)
                    
                    except json.JSONDecodeError:
                        st.error("Invalid JSON in parameters")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

def main():
    """Main application"""
    init_session_state()
    
    # Check authentication
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Sidebar navigation
    selected_page = sidebar_config()
    
    # Route to appropriate page based on subscription status
    if st.session_state.user_data['subscription_status'] == 'inactive':
        upgrade_required_page()
    elif selected_page == "Dashboard":
        dashboard_page()
    elif selected_page == "Property Analytics":
        property_analytics_page()
    elif selected_page == "Market Insights":
        market_insights_page()
    elif selected_page == "User Management":
        user_management_page()
    elif selected_page == "WooCommerce":
        woocommerce_integration_page()
    elif selected_page == "Upgrade Required":
        upgrade_required_page()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p><strong>🏠 AI PropIQ Dashboard</strong> | Premium Real Estate Intelligence Platform</p>
        <p><small>Powered by Advanced Analytics & Machine Learning | Product ID: 190</small></p>
        <p><small>For support, visit <a href="https://aipropiq.com" target="_blank">aipropiq.com</a></small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
