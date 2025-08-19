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
    page_title="AI PropIQ Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WordPressWooCommerceAPI:
    def __init__(self):
        # Use Streamlit secrets for configuration
        self.base_url = st.secrets["wordpress"]["base_url"]
        self.consumer_key = st.secrets["woocommerce"]["consumer_key"]
        self.consumer_secret = st.secrets["woocommerce"]["consumer_secret"]
        self.jwt_secret = st.secrets["jwt"]["secret_key"]
        
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
                    'user_display_name': data.get('user_display_name')
                }
            else:
                return {'success': False, 'message': 'Invalid credentials'}
                
        except Exception as e:
            return {'success': False, 'message': f'Authentication error: {str(e)}'}
    
    def check_subscription_status(self, user_email):
        """Check if user has active subscription for Product ID 190"""
        try:
            # Get all subscriptions
            subscriptions_url = f"{self.base_url}/wp-json/wc/v3/subscriptions"
            
            response = requests.get(
                subscriptions_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'per_page': 100}
            )
            
            if response.status_code == 200:
                subscriptions = response.json()
                
                for subscription in subscriptions:
                    if subscription.get('billing', {}).get('email') == user_email:
                        # Check if subscription contains Product ID 190
                        for item in subscription.get('line_items', []):
                            if item.get('product_id') == 190:
                                return {
                                    'has_subscription': True,
                                    'status': subscription.get('status'),
                                    'subscription_id': subscription.get('id'),
                                    'next_payment': subscription.get('next_payment_date'),
                                    'total': subscription.get('total')
                                }
                
                return {'has_subscription': False}
            else:
                return {'has_subscription': False, 'error': 'API Error'}
                
        except Exception as e:
            return {'has_subscription': False, 'error': str(e)}
    
    def get_customers(self):
        """Get all WooCommerce customers"""
        try:
            customers_url = f"{self.base_url}/wp-json/wc/v3/customers"
            
            response = requests.get(
                customers_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'per_page': 100}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            st.error(f"Error fetching customers: {str(e)}")
            return []
    
    def get_products(self):
        """Get all WooCommerce products"""
        try:
            products_url = f"{self.base_url}/wp-json/wc/v3/products"
            
            response = requests.get(
                products_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'per_page': 100}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            st.error(f"Error fetching products: {str(e)}")
            return []
    
    def get_orders(self):
        """Get all WooCommerce orders"""
        try:
            orders_url = f"{self.base_url}/wp-json/wc/v3/orders"
            
            response = requests.get(
                orders_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'per_page': 100}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            st.error(f"Error fetching orders: {str(e)}")
            return []

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
    }
    
    .dashboard-card {
        background: rgba(255, 255, 255, 0.9);
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    
    .success-message {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .error-message {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .sidebar .sidebar-content {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        padding: 1rem;
    }
    
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    
    .property-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #667eea;
    }
    
    .status-active {
        background: #4CAF50;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-inactive {
        background: #f44336;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

def login_page():
    """Display login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("# 🏠 AI PropIQ Dashboard")
        st.markdown("### Welcome Back!")
        st.markdown("Please login to access your dashboard")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("Login", use_container_width=True)
            
            if submit_button:
                if username and password:
                    api = WordPressWooCommerceAPI()
                    result = api.authenticate_user(username, password)
                    
                    if result['success']:
                        # Check subscription status
                        subscription_status = api.check_subscription_status(result['user_email'])
                        
                        if subscription_status.get('has_subscription'):
                            st.session_state.authenticated = True
                            st.session_state.user_data = result
                            st.session_state.subscription_data = subscription_status
                            st.success("Login successful! Redirecting...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Access denied. You need an active subscription for Product ID 190.")
                    else:
                        st.error(result['message'])
                else:
                    st.error("Please enter both username and password")
    
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard_page():
    """Display main dashboard"""
    st.markdown("# 🏠 AI PropIQ Dashboard")
    st.markdown(f"Welcome back, **{st.session_state.user_data['user_display_name']}**!")
    
    # Subscription status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>Subscription Status</h3>
            <h2>Active</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Next Payment</h3>
            <h2>{st.session_state.subscription_data.get('next_payment', 'N/A')}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Subscription ID</h3>
            <h2>{st.session_state.subscription_data.get('subscription_id', 'N/A')}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Total Amount</h3>
            <h2>${st.session_state.subscription_data.get('total', '0')}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Property Analytics Section
    st.markdown("## 📊 Property Analytics")
    
    # Sample property data for demonstration
    property_data = {
        'Property': ['Downtown Condo', 'Suburban House', 'City Apartment', 'Beach House', 'Mountain Cabin'],
        'Value': [450000, 320000, 280000, 750000, 180000],
        'ROI': [8.5, 12.3, 6.7, 15.2, 9.8],
        'Status': ['Active', 'Active', 'Pending', 'Active', 'Inactive']
    }
    
    df = pd.DataFrame(property_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Property value chart
        fig_value = px.bar(df, x='Property', y='Value', title='Property Values',
                          color='Value', color_continuous_scale='viridis')
        fig_value.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        st.plotly_chart(fig_value, use_container_width=True)
    
    with col2:
        # ROI chart
        fig_roi = px.scatter(df, x='Value', y='ROI', size='ROI', color='Status',
                            title='Property ROI vs Value', hover_name='Property')
        fig_roi.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2c3e50')
        )
        st.plotly_chart(fig_roi, use_container_width=True)
    
    # Property list
    st.markdown("## 🏘️ Property Portfolio")
    
    for index, row in df.iterrows():
        status_class = "status-active" if row['Status'] == 'Active' else "status-inactive"
        
        st.markdown(f"""
        <div class="property-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3>{row['Property']}</h3>
                    <p><strong>Value:</strong> ${row['Value']:,}</p>
                    <p><strong>ROI:</strong> {row['ROI']}%</p>
                </div>
                <div>
                    <span class="{status_class}">{row['Status']}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def user_management_page():
    """Display user management page"""
    st.markdown("# 👥 User Management")
    
    api = WordPressWooCommerceAPI()
    
    # Get customers
    with st.spinner("Loading customers..."):
        customers = api.get_customers()
    
    if customers:
        st.markdown(f"## Total Customers: {len(customers)}")
        
        # Create DataFrame
        customer_data = []
        for customer in customers:
            customer_data.append({
                'ID': customer.get('id'),
                'Name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                'Email': customer.get('email'),
                'Username': customer.get('username'),
                'Orders': customer.get('orders_count', 0),
                'Total Spent': f"${customer.get('total_spent', 0)}",
                'Date Created': customer.get('date_created', '').split('T')[0] if customer.get('date_created') else ''
            })
        
        df_customers = pd.DataFrame(customer_data)
        
        # Display customers table
        st.dataframe(df_customers, use_container_width=True)
        
        # Customer analytics
        col1, col2 = st.columns(2)
        
        with col1:
            # Orders distribution
            fig_orders = px.histogram(df_customers, x='Orders', title='Orders Distribution',
                                    nbins=20, color_discrete_sequence=['#667eea'])
            fig_orders.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            st.plotly_chart(fig_orders, use_container_width=True)
        
        with col2:
            # Registration timeline
            df_customers['Date Created'] = pd.to_datetime(df_customers['Date Created'])
            registrations_by_month = df_customers.groupby(df_customers['Date Created'].dt.to_period('M')).size()
            
            fig_timeline = px.line(x=registrations_by_month.index.astype(str), 
                                 y=registrations_by_month.values,
                                 title='Customer Registrations Over Time')
            fig_timeline.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    else:
        st.warning("No customers found or unable to fetch customer data.")

def products_page():
    """Display products management page"""
    st.markdown("# 🛍️ Products Management")
    
    api = WordPressWooCommerceAPI()
    
    # Get products
    with st.spinner("Loading products..."):
        products = api.get_products()
    
    if products:
        st.markdown(f"## Total Products: {len(products)}")
        
        # Create DataFrame
        product_data = []
        for product in products:
            product_data.append({
                'ID': product.get('id'),
                'Name': product.get('name'),
                'Price': f"${product.get('price', 0)}",
                'Regular Price': f"${product.get('regular_price', 0)}",
                'Status': product.get('status'),
                'Stock Status': product.get('stock_status'),
                'Categories': ', '.join([cat.get('name', '') for cat in product.get('categories', [])]),
                'Date Created': product.get('date_created', '').split('T')[0] if product.get('date_created') else ''
            })
        
        df_products = pd.DataFrame(product_data)
        
        # Display products table
        st.dataframe(df_products, use_container_width=True)
        
        # Product analytics
        col1, col2 = st.columns(2)
        
        with col1:
            # Price distribution
            prices = [float(p.get('price', 0)) for p in products if p.get('price')]
            if prices:
                fig_prices = px.histogram(x=prices, title='Price Distribution',
                                        nbins=20, color_discrete_sequence=['#764ba2'])
                fig_prices.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#2c3e50')
                )
                st.plotly_chart(fig_prices, use_container_width=True)
        
        with col2:
            # Status distribution
            status_counts = df_products['Status'].value_counts()
            fig_status = px.pie(values=status_counts.values, names=status_counts.index,
                              title='Product Status Distribution')
            fig_status.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            st.plotly_chart(fig_status, use_container_width=True)
    
    else:
        st.warning("No products found or unable to fetch product data.")

def orders_page():
    """Display orders management page"""
    st.markdown("# 📦 Orders Management")
    
    api = WordPressWooCommerceAPI()
    
    # Get orders
    with st.spinner("Loading orders..."):
        orders = api.get_orders()
    
    if orders:
        st.markdown(f"## Total Orders: {len(orders)}")
        
        # Create DataFrame
        order_data = []
        for order in orders:
            order_data.append({
                'ID': order.get('id'),
                'Status': order.get('status'),
                'Total': f"${order.get('total', 0)}",
                'Customer': f"{order.get('billing', {}).get('first_name', '')} {order.get('billing', {}).get('last_name', '')}".strip(),
                'Email': order.get('billing', {}).get('email', ''),
                'Payment Method': order.get('payment_method_title', ''),
                'Date Created': order.get('date_created', '').split('T')[0] if order.get('date_created') else ''
            })
        
        df_orders = pd.DataFrame(order_data)
        
        # Display orders table
        st.dataframe(df_orders, use_container_width=True)
        
        # Order analytics
        col1, col2 = st.columns(2)
        
        with col1:
            # Status distribution
            status_counts = df_orders['Status'].value_counts()
            fig_status = px.bar(x=status_counts.index, y=status_counts.values,
                              title='Order Status Distribution',
                              color=status_counts.values, color_continuous_scale='viridis')
            fig_status.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Revenue over time
            df_orders['Date Created'] = pd.to_datetime(df_orders['Date Created'])
            df_orders['Total_Numeric'] = df_orders['Total'].str.replace('$', '').astype(float)
            revenue_by_date = df_orders.groupby('Date Created')['Total_Numeric'].sum()
            
            fig_revenue = px.line(x=revenue_by_date.index, y=revenue_by_date.values,
                                title='Revenue Over Time')
            fig_revenue.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50')
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
    
    else:
        st.warning("No orders found or unable to fetch order data.")

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
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("# 🏠 AI PropIQ")
        st.markdown(f"**User:** {st.session_state.user_data['user_display_name']}")
        st.markdown(f"**Email:** {st.session_state.user_data['user_email']}")
        st.markdown("---")
        
        page = st.selectbox(
            "Navigate to:",
            ["Dashboard", "User Management", "Products", "Orders"]
        )
        
        st.markdown("---")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.session_state.subscription_data = None
            st.rerun()
    
    # Display selected page
    if page == "Dashboard":
        dashboard_page()
    elif page == "User Management":
        user_management_page()
    elif page == "Products":
        products_page()
    elif page == "Orders":
        orders_page()

if __name__ == "__main__":
    main()
