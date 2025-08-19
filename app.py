import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import time

# ---------------------------
# Page configuration
# ---------------------------
st.set_page_config(
    page_title="AI PropIQ Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# API Wrapper
# ---------------------------
class WordPressWooCommerceAPI:
    def __init__(self):
        # Use Streamlit secrets for configuration
        wp_secrets = st.secrets.get("wordpress", {})
        wc_secrets = st.secrets.get("woocommerce", {})
        jwt_secrets = st.secrets.get("jwt", {})  # may be missing

        self.base_url = wp_secrets.get("base_url", "").rstrip("/")
        if not self.base_url:
            st.stop()  # fail fast, this is required

        self.consumer_key = wc_secrets.get("consumer_key", "")
        self.consumer_secret = wc_secrets.get("consumer_secret", "")
        # Optional – only needed if you create your own tokens
        self.jwt_secret = jwt_secrets.get("secret_key", None)

    # ---- WordPress Auth (JWT) ----
    def authenticate_user(self, username, password):
        """Authenticate user with WordPress JWT plugin"""
        auth_url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
        try:
            response = requests.post(
                auth_url,
                json={"username": username, "password": password},
                timeout=20
            )
            if response.status_code == 200:
                data = response.json()
                # Typical fields: token, user_email, user_nicename, user_display_name
                return {
                    "success": True,
                    "token": data.get("token"),
                    "user_email": data.get("user_email"),
                    "user_nicename": data.get("user_nicename"),
                    "user_display_name": data.get("user_display_name")
                }
            else:
                # Surface API message if present
                try:
                    msg = response.json().get("message", "Invalid credentials")
                except Exception:
                    msg = "Invalid credentials"
                return {"success": False, "message": msg}
        except Exception as e:
            return {"success": False, "message": f"Authentication error: {str(e)}"}

    def check_user_is_subscriber(self, token):
        """
        Use the JWT token to fetch the current user and verify the 'subscriber' role.
        This avoids requiring admin-level WooCommerce REST keys to list users.
        """
        try:
            me_url = f"{self.base_url}/wp-json/wp/v2/users/me"
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(me_url, headers=headers, timeout=20)

            if resp.status_code == 200:
                me = resp.json()
                roles = me.get("roles", []) or []
                is_subscriber = "subscriber" in roles
                return {
                    "has_access": is_subscriber,
                    "role": roles,
                    "user_id": me.get("id"),
                    "username": me.get("slug") or me.get("name"),
                    "email": me.get("email")
                }
            else:
                return {
                    "has_access": False,
                    "error": f"WP users/me error {resp.status_code}: {resp.text}"
                }
        except Exception as e:
            return {"has_access": False, "error": str(e)}

    # ---- WooCommerce Data ----
    def get_customers(self):
        """Get WooCommerce customers (requires WooCommerce REST keys with read perms)"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/customers"
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                params={"per_page": 100},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            st.error(f"Error fetching customers: {str(e)}")
            return []

    def get_products(self):
        """Get WooCommerce products"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/products"
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                params={"per_page": 100},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            st.error(f"Error fetching products: {str(e)}")
            return []

    def get_orders(self):
        """Get WooCommerce orders"""
        try:
            url = f"{self.base_url}/wp-json/wc/v3/orders"
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                params={"per_page": 100},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            st.error(f"Error fetching orders: {str(e)}")
            return []

# ---------------------------
# Styles
# ---------------------------
def apply_custom_css():
    st.markdown(
        """
        <style>
        .main { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
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
            color: white; padding: 1.5rem; border-radius: 10px; text-align: center;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        .status-active { background: #4CAF50; color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
        .status-inactive { background: #f44336; color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        h1, h2, h3 { color: #2c3e50; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True
    )

# ---------------------------
# Pages
# ---------------------------
def login_page():
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

                    if result.get("success"):
                        # Check WP role = subscriber using the returned JWT token
                        access = api.check_user_is_subscriber(result["token"])

                        if access.get("has_access"):
                            st.session_state.authenticated = True
                            st.session_state.user_data = {
                                "user_display_name": result.get("user_display_name") or username,
                                "user_email": result.get("user_email"),
                                "token": result.get("token"),
                                "roles": access.get("role", []),
                                "user_id": access.get("user_id"),
                                "username": access.get("username"),
                            }
                            # Keep a small dict for the dashboard "status" tiles
                            st.session_state.subscription_data = {
                                "role": access.get("role", []),
                                "status": "subscriber" if "subscriber" in (access.get("role") or []) else "unauthorized"
                            }
                            st.success("Login successful! Redirecting...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            err = access.get("error")
                            if err:
                                st.error(f"Access check failed: {err}")
                            else:
                                st.error("Access denied. You must be a WordPress user with the role 'subscriber'.")
                    else:
                        st.error(result.get("message", "Login failed"))
                else:
                    st.error("Please enter both username and password")

    st.markdown("</div>", unsafe_allow_html=True)

def dashboard_page():
    st.markdown("# 🏠 AI PropIQ Dashboard")
    st.markdown(f"Welcome back, **{st.session_state.user_data.get('user_display_name', 'User')}**!")

    role_text = ", ".join(st.session_state.user_data.get("roles", [])) or "—"
    status_text = "Active" if "subscriber" in st.session_state.user_data.get("roles", []) else "Inactive"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Access</h3>
                <h2>{status_text}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Role(s)</h3>
                <h2>{role_text}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>User ID</h3>
                <h2>{st.session_state.user_data.get('user_id', 'N/A')}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Username</h3>
                <h2>{st.session_state.user_data.get('username', 'N/A')}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("## 📊 Property Analytics")

    # Sample property data for demonstration
    property_data = {
        "Property": ["Downtown Condo", "Suburban House", "City Apartment", "Beach House", "Mountain Cabin"],
        "Value": [450000, 320000, 280000, 750000, 180000],
        "ROI": [8.5, 12.3, 6.7, 15.2, 9.8],
        "Status": ["Active", "Active", "Pending", "Active", "Inactive"],
    }
    df = pd.DataFrame(property_data)

    c1, c2 = st.columns(2)
    with c1:
        fig_value = px.bar(df, x="Property", y="Value", title="Property Values", color="Value", color_continuous_scale="viridis")
        fig_value.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
        st.plotly_chart(fig_value, use_container_width=True)

    with c2:
        fig_roi = px.scatter(df, x="Value", y="ROI", size="ROI", color="Status", title="Property ROI vs Value", hover_name="Property")
        fig_roi.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
        st.plotly_chart(fig_roi, use_container_width=True)

    st.markdown("## 🏘️ Property Portfolio")
    for _, row in df.iterrows():
        status_class = "status-active" if row["Status"] == "Active" else "status-inactive"
        st.markdown(
            f"""
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
            """,
            unsafe_allow_html=True
        )

def user_management_page():
    st.markdown("# 👥 User Management")
    api = WordPressWooCommerceAPI()
    with st.spinner("Loading customers..."):
        customers = api.get_customers()

    if customers:
        st.markdown(f"## Total Customers: {len(customers)}")
        rows = []
        for c in customers:
            rows.append({
                "ID": c.get("id"),
                "Name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "Email": c.get("email"),
                "Username": c.get("username"),
                "Orders": c.get("orders_count", 0),
                "Total Spent": f"${c.get('total_spent', 0)}",
                "Date Created": (c.get("date_created") or "").split("T")[0] if c.get("date_created") else ""
            })
        df_customers = pd.DataFrame(rows)
        st.dataframe(df_customers, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            fig_orders = px.histogram(df_customers, x="Orders", title="Orders Distribution", nbins=20, color_discrete_sequence=["#667eea"])
            fig_orders.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
            st.plotly_chart(fig_orders, use_container_width=True)

        with c2:
            if not df_customers.empty:
                df_customers["Date Created"] = pd.to_datetime(df_customers["Date Created"], errors="coerce")
                registrations_by_month = df_customers.dropna(subset=["Date Created"]).groupby(df_customers["Date Created"].dt.to_period("M")).size()
                fig_timeline = px.line(x=registrations_by_month.index.astype(str), y=registrations_by_month.values, title="Customer Registrations Over Time")
                fig_timeline.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
                st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.warning("No customers found or unable to fetch customer data.")

def products_page():
    st.markdown("# 🛍️ Products Management")
    api = WordPressWooCommerceAPI()
    with st.spinner("Loading products..."):
        products = api.get_products()

    if products:
        st.markdown(f"## Total Products: {len(products)}")
        rows = []
        for p in products:
            rows.append({
                "ID": p.get("id"),
                "Name": p.get("name"),
                "Price": f"${p.get('price', 0)}",
                "Regular Price": f"${p.get('regular_price', 0)}",
                "Status": p.get("status"),
                "Stock Status": p.get("stock_status"),
                "Categories": ", ".join([cat.get("name", "") for cat in p.get("categories", [])]),
                "Date Created": (p.get("date_created") or "").split("T")[0] if p.get("date_created") else ""
            })
        df_products = pd.DataFrame(rows)
        st.dataframe(df_products, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            prices = []
            for p in products:
                val = p.get("price")
                try:
                    if val is not None and str(val) != "":
                        prices.append(float(val))
                except Exception:
                    pass
            if prices:
                fig_prices = px.histogram(x=prices, title="Price Distribution", nbins=20, color_discrete_sequence=["#764ba2"])
                fig_prices.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
                st.plotly_chart(fig_prices, use_container_width=True)

        with c2:
            status_counts = df_products["Status"].value_counts()
            fig_status = px.pie(values=status_counts.values, names=status_counts.index, title="Product Status Distribution")
            fig_status.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
            st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.warning("No products found or unable to fetch product data.")

def orders_page():
    st.markdown("# 📦 Orders Management")
    api = WordPressWooCommerceAPI()
    with st.spinner("Loading orders..."):
        orders = api.get_orders()

    if orders:
        st.markdown(f"## Total Orders: {len(orders)}")
        rows = []
        for o in orders:
            rows.append({
                "ID": o.get("id"),
                "Status": o.get("status"),
                "Total": f"${o.get('total', 0)}",
                "Customer": f"{o.get('billing', {}).get('first_name', '')} {o.get('billing', {}).get('last_name', '')}".strip(),
                "Email": o.get("billing", {}).get("email", ""),
                "Payment Method": o.get("payment_method_title", ""),
                "Date Created": (o.get("date_created") or "").split("T")[0] if o.get("date_created") else ""
            })
        df_orders = pd.DataFrame(rows)
        st.dataframe(df_orders, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            status_counts = df_orders["Status"].value_counts()
            fig_status = px.bar(x=status_counts.index, y=status_counts.values, title="Order Status Distribution", color=status_counts.values, color_continuous_scale="viridis")
            fig_status.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
            st.plotly_chart(fig_status, use_container_width=True)

        with c2:
            if not df_orders.empty:
                df_orders["Date Created"] = pd.to_datetime(df_orders["Date Created"], errors="coerce")
                # Parse currency safely
                def to_float(x):
                    if pd.isna(x): return 0.0
                    s = str(x).replace("$", "").replace(",", "").strip()
                    try: return float(s)
                    except: return 0.0
                df_orders["Total_Numeric"] = df_orders["Total"].apply(to_float)
                revenue_by_date = df_orders.dropna(subset=["Date Created"]).groupby("Date Created")["Total_Numeric"].sum()
                fig_revenue = px.line(x=revenue_by_date.index, y=revenue_by_date.values, title="Revenue Over Time")
                fig_revenue.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#2c3e50"))
                st.plotly_chart(fig_revenue, use_container_width=True)
    else:
        st.warning("No orders found or unable to fetch order data.")

# ---------------------------
# Main
# ---------------------------
def apply_custom_css_and_init():
    apply_custom_css()
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

def main():
    apply_custom_css_and_init()

    if not st.session_state.authenticated:
        login_page()
        return

    with st.sidebar:
        st.markdown("# 🏠 AI PropIQ")
        st.markdown(f"**User:** {st.session_state.user_data.get('user_display_name', '—')}")
        st.markdown(f"**Email:** {st.session_state.user_data.get('user_email', '—')}")
        st.markdown("---")

        page = st.selectbox("Navigate to:", ["Dashboard", "User Management", "Products", "Orders"])
        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

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
