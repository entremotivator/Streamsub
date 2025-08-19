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
    
    def check_user_role(self, user_email, required_role='subscriber'):
        """Check if user has required WordPress role"""
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
                        has_role = required_role in roles or 'administrator' in roles
                        return {
                            'has_role': has_role,
                            'user_id': user.get('id'),
                            'username': user.get('username'),
                            'email': user.get('email'),
                            'roles': roles,
                            'is_admin': 'administrator' in roles
                        }
                        
                return {'has_role': False, 'message': f'User does not have {required_role} role'}
            else:
                return {'has_role': False, 'message': f"API Error: {response.status_code}"}
                
        except Exception as e:
            return {'has_role': False, 'message': f'Error checking user role: {str(e)}'}
    
    def create_wordpress_user(self, username, email, password, first_name="", last_name="", role="subscriber"):
        """Create new WordPress user"""
        try:
            users_url = f"{self.base_url}/wp-json/wp/v2/users"
            
            user_data = {
                'username': username,
                'email': email,
                'password': password,
                'first_name': first_name,
                'last_name': last_name,
                'roles': [role]
            }
            
            response = requests.post(
                users_url,
                auth=(self.consumer_key, self.consumer_secret),
                json=user_data
            )
            
            if response.status_code == 201:
                return {
                    'success': True,
                    'user_data': response.json(),
                    'message': f'User {username} created successfully'
                }
            else:
                error_data = response.json()
                return {
                    'success': False,
                    'message': error_data.get('message', f'Error creating user: {response.status_code}')
                }
                
        except Exception as e:
            return {'success': False, 'message': f'Error creating WordPress user: {str(e)}'}
    
    def get_all_wordpress_users(self):
        """Get all WordPress users"""
        try:
            users_url = f"{self.base_url}/wp-json/wp/v2/users"
            
            response = requests.get(
                users_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'per_page': 100}  # Adjust as needed
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            st.error(f"Error fetching users: {str(e)}")
            return []
    
    def update_user_role(self, user_id, new_role):
        """Update WordPress user role"""
        try:
            user_url = f"{self.base_url}/wp-json/wp/v2/users/{user_id}"
            
            response = requests.post(
                user_url,
                auth=(self.consumer_key, self.consumer_secret),
                json={'roles': [new_role]}
            )
            
            if response.status_code == 200:
                return {'success': True, 'message': f'User role updated to {new_role}'}
            else:
                return {'success': False, 'message': f'Error updating role: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error updating user role: {str(e)}'}
    
    def delete_wordpress_user(self, user_id):
        """Delete WordPress user"""
        try:
            user_url = f"{self.base_url}/wp-json/wp/v2/users/{user_id}"
            
            response = requests.delete(
                user_url,
                auth=(self.consumer_key, self.consumer_secret),
                params={'force': True, 'reassign': 1}  # Force delete and reassign posts to admin
            )
            
            if response.status_code == 200:
                return {'success': True, 'message': 'User deleted successfully'}
            else:
                return {'success': False, 'message': f'Error deleting user: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error deleting user: {str(e)}'}
    
    def generate_secure_password(self, length=12):
        """Generate secure password"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))
    
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
                    return customers[0]
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

def apply_enhanced_css():
    """Apply enhanced custom CSS styling"""
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
    
    .admin-panel {
        background: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 1rem;
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
    
    .admin-card {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        margin: 1rem 0;
    }
    
    .user-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #2196F3;
    }
    
    .payment-info {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #4CAF50;
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
    
    .admin-button {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%) !important;
    }
    
    .danger-button {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%) !important;
    }
    </style>
    """, unsafe_allow_html=True)

def login_page():
    """Display enhanced login page with admin/subscriber options"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("# 🏠 AI PropIQ")
    st.markdown("### WordPress Admin & Subscriber Portal")
    
    # Login type selection
    login_type = st.radio("Select Login Type:", ["Subscriber Access", "Admin Panel"], horizontal=True)
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your WordPress username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button(f"Login as {login_type.split()[0]}")
        
        if submit_button:
            if username and password:
                admin_manager = WordPressAdminManager()
                
                # Authenticate user
                auth_result = admin_manager.authenticate_user(username, password)
                
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
                    st.error(f"❌ Login failed: {auth_result['message']}")
            else:
                st.error("Please enter both username and password")
    
    st.markdown('</div>', unsafe_allow_html=True)

def admin_dashboard():
    """Display WordPress admin dashboard"""
    st.markdown("# 🛠️ WordPress Admin Panel")
    st.markdown(f"Welcome, **{st.session_state.user_data['user_display_name']}** (Administrator)")
    
    admin_manager = WordPressAdminManager()
    
    # Admin stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="admin-card">
            <h3>👑 Admin Status</h3>
            <h2>Active</h2>
            <p>Full Access</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        users = admin_manager.get_all_wordpress_users()
        st.markdown(f"""
        <div class="admin-card">
            <h3>👥 Total Users</h3>
            <h2>{len(users)}</h2>
            <p>WordPress Users</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        subscribers = [u for u in users if 'subscriber' in u.get('roles', [])]
        st.markdown(f"""
        <div class="admin-card">
            <h3>📝 Subscribers</h3>
            <h2>{len(subscribers)}</h2>
            <p>Active Subscribers</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="admin-card">
            <h3>🎯 Product ID</h3>
            <h2>{admin_manager.product_id}</h2>
            <p>Target Product</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Admin tabs
    tab1, tab2, tab3 = st.tabs(["👥 User Management", "➕ Add New User", "📊 Analytics"])
    
    with tab1:
        st.markdown("## User Management")
        
        if users:
            # User management table
            user_data = []
            for user in users:
                user_data.append({
                    'ID': user.get('id'),
                    'Username': user.get('username'),
                    'Email': user.get('email'),
                    'Name': user.get('name', ''),
                    'Roles': ', '.join(user.get('roles', [])),
                    'Registered': user.get('registered_date', '').split('T')[0] if user.get('registered_date') else 'N/A'
                })
            
            df_users = pd.DataFrame(user_data)
            st.dataframe(df_users, use_container_width=True)
            
            # User actions
            st.markdown("### User Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Update User Role")
                selected_user_id = st.selectbox("Select User", options=[u['ID'] for u in user_data], format_func=lambda x: f"ID {x} - {next(u['Username'] for u in user_data if u['ID'] == x)}")
                new_role = st.selectbox("New Role", ["subscriber", "contributor", "author", "editor", "administrator"])
                
                if st.button("Update Role", key="update_role"):
                    result = admin_manager.update_user_role(selected_user_id, new_role)
                    if result['success']:
                        st.success(result['message'])
                        st.rerun()
                    else:
                        st.error(result['message'])
            
            with col2:
                st.markdown("#### Delete User")
                delete_user_id = st.selectbox("Select User to Delete", options=[u['ID'] for u in user_data], format_func=lambda x: f"ID {x} - {next(u['Username'] for u in user_data if u['ID'] == x)}", key="delete_select")
                
                if st.button("🗑️ Delete User", key="delete_user", type="secondary"):
                    if st.session_state.get('confirm_delete'):
                        result = admin_manager.delete_wordpress_user(delete_user_id)
                        if result['success']:
                            st.success(result['message'])
                            st.session_state.confirm_delete = False
                            st.rerun()
                        else:
                            st.error(result['message'])
                    else:
                        st.session_state.confirm_delete = True
                        st.warning("Click again to confirm deletion")
        else:
            st.warning("No users found")
    
    with tab2:
        st.markdown("## Add New WordPress User")
        
        st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username*", placeholder="Enter username")
                new_email = st.text_input("Email*", placeholder="Enter email address")
                new_first_name = st.text_input("First Name", placeholder="Enter first name")
            
            with col2:
                new_password = st.text_input("Password*", type="password", placeholder="Enter password")
                new_last_name = st.text_input("Last Name", placeholder="Enter last name")
                new_role = st.selectbox("User Role", ["subscriber", "contributor", "author", "editor", "administrator"], index=0)
            
            # Password generator
            col_gen1, col_gen2 = st.columns([3, 1])
            with col_gen2:
                if st.form_submit_button("🔐 Generate Password"):
                    generated_password = admin_manager.generate_secure_password()
                    st.session_state.generated_password = generated_password
            
            if 'generated_password' in st.session_state:
                st.info(f"Generated Password: `{st.session_state.generated_password}`")
                if st.checkbox("Use generated password"):
                    new_password = st.session_state.generated_password
            
            submit_new_user = st.form_submit_button("➕ Create WordPress User", type="primary")
            
            if submit_new_user:
                if new_username and new_email and new_password:
                    # Create WordPress user
                    result = admin_manager.create_wordpress_user(
                        username=new_username,
                        email=new_email,
                        password=new_password,
                        first_name=new_first_name,
                        last_name=new_last_name,
                        role=new_role
                    )
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        st.json(result['user_data'])
                        
                        # Clear generated password
                        if 'generated_password' in st.session_state:
                            del st.session_state.generated_password
                        
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ {result['message']}")
                else:
                    st.error("Please fill in all required fields (Username, Email, Password)")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown("## User Analytics")
        
        if users:
            # Role distribution
            role_counts = {}
            for user in users:
                for role in user.get('roles', []):
                    role_counts[role] = role_counts.get(role, 0) + 1
            
            if role_counts:
                fig_roles = px.pie(
                    values=list(role_counts.values()),
                    names=list(role_counts.keys()),
                    title="User Role Distribution"
                )
                st.plotly_chart(fig_roles, use_container_width=True)
            
            # Registration timeline (if date available)
            reg_dates = []
            for user in users:
                reg_date = user.get('registered_date', '')
                if reg_date:
                    reg_dates.append(reg_date.split('T')[0])
            
            if reg_dates:
                df_reg = pd.DataFrame({'date': reg_dates})
                df_reg['date'] = pd.to_datetime(df_reg['date'])
                df_reg['count'] = 1
                df_reg_grouped = df_reg.groupby(df_reg['date'].dt.date).count().reset_index()
                
                fig_timeline = px.line(
                    df_reg_grouped,
                    x='date',
                    y='count',
                    title="User Registration Timeline"
                )
                st.plotly_chart(fig_timeline, use_container_width=True)

def subscriber_dashboard():
    """Display subscriber dashboard with product and payment info"""
    st.markdown("# 🏠 AI PropIQ - Subscriber Dashboard")
    st.markdown(f"Welcome, **{st.session_state.user_data['user_display_name']}**!")
    
    admin_manager = WordPressAdminManager()
    
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
    
    product_info = admin_manager.get_product_info(st.session_state.product_id)
    
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
            orders = admin_manager.get_customer_orders(customer.get('id'))
            
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

def main():
    """Main application function"""
    apply_enhanced_css()
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
    # Check authentication
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Sidebar for authenticated users
    with st.sidebar:
        st.markdown("# 🏠 AI PropIQ")
        
        if st.session_state.is_admin:
            st.markdown("## 👑 Admin Panel")
            st.markdown(f"**Admin:** {st.session_state.user_data['user_display_name']}")
            st.markdown(f"**Email:** {st.session_state.user_data['user_email']}")
            st.markdown("**Role:** Administrator")
        else:
            st.markdown("## 📝 Subscriber Portal")
            st.markdown(f"**Subscriber:** {st.session_state.user_data['user_display_name']}")
            st.markdown(f"**Email:** {st.session_state.user_data['user_email']}")
            st.markdown(f"**Product ID:** {st.session_state.product_id}")
        
        st.markdown("---")
        
        if st.session_state.is_admin:
            st.markdown("### 🛠️ Admin Tools")
            st.markdown("- User Management")
            st.markdown("- Add New Users")
            st.markdown("- Analytics Dashboard")
            st.markdown("- WordPress Sync")
        else:
            st.markdown("### 📊 Quick Stats")
            if st.session_state.get('customer_data'):
                st.metric("Total Orders", st.session_state.customer_data.get('orders_count', 0))
                st.metric("Total Spent", f"${st.session_state.customer_data.get('total_spent', '0')}")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Display appropriate dashboard
    if st.session_state.is_admin:
        admin_dashboard()
    else:
        subscriber_dashboard()

if __name__ == "__main__":
    main()
