"""Authentication module for the ETF & Stock AI Tracker dashboard.

Provides login, registration, and session management using
streamlit-authenticator backed by a local YAML credentials file.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import yaml

# Path to the credentials file (project root)
_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CREDENTIALS_PATH = _ROOT / "auth_config.yaml"


def _build_default_config() -> dict:
    """Build the default auth configuration with a random cookie key."""
    return {
        "credentials": {
            "usernames": {
                "admin": {
                    "email": "admin@example.com",
                    "first_name": "Admin",
                    "last_name": "User",
                    "password": "admin",
                    "roles": ["admin"],
                }
            }
        },
        "cookie": {
            "expiry_days": 30,
            "key": secrets.token_hex(32),
            "name": "etf_stock_tracker_auth",
        },
    }


def _credentials_path() -> Path:
    """Return the path to the credentials file, honouring an env override."""
    return Path(os.environ.get("AUTH_CONFIG_PATH", str(_DEFAULT_CREDENTIALS_PATH)))


def _ensure_config_exists() -> None:
    """Create the default credentials file if it does not yet exist."""
    path = _credentials_path()
    if not path.exists():
        config = _build_default_config()
        with open(path, "w") as fh:
            yaml.dump(config, fh, default_flow_style=False)


def load_config() -> dict:
    """Load and return the authentication configuration dictionary."""
    _ensure_config_exists()
    with open(_credentials_path()) as fh:
        return yaml.safe_load(fh)


def save_config(config: dict) -> None:
    """Persist the (possibly updated) configuration back to disk."""
    with open(_credentials_path(), "w") as fh:
        yaml.dump(config, fh, default_flow_style=False)


def get_authenticator(config: dict) -> stauth.Authenticate:
    """Return a configured ``Authenticate`` instance, reusing one from session state."""
    if "_authenticator" not in st.session_state:
        st.session_state["_authenticator"] = stauth.Authenticate(
            credentials=config["credentials"],
            cookie_name=config["cookie"]["name"],
            cookie_key=config["cookie"]["key"],
            cookie_expiry_days=config["cookie"]["expiry_days"],
            auto_hash=True,
        )
    return st.session_state["_authenticator"]


def render_login_page() -> bool:
    """Show the login / register UI and return *True* when authenticated.

    The function renders a tabbed interface with a *Login* tab and a
    *Create Account* tab.  After a successful registration the updated
    credentials are written back to the YAML file so they survive
    restarts.
    """
    config = load_config()
    authenticator = get_authenticator(config)

    # If already authenticated (e.g. via cookie), skip the login UI.
    if st.session_state.get("authentication_status") is True:
        return True

    st.title("📈 ETF & Stock AI Tracker")
    st.subheader("Please log in to continue")

    login_tab, register_tab = st.tabs(["🔑 Login", "📝 Create Account"])

    with login_tab:
        authenticator.login(location="main")

    if st.session_state.get("authentication_status") is True:
        st.rerun()

    if st.session_state.get("authentication_status") is False:
        st.error("❌ Username or password is incorrect.")

    with register_tab:
        try:
            # register_user returns (email, username, name) on success
            email, username, name = authenticator.register_user(
                location="main",
                pre_authorized=[],
                captcha=False,
            )
            if email:
                # Persist the updated credentials from the authenticator
                model = authenticator.authentication_controller.authentication_model
                config["credentials"] = model.credentials
                save_config(config)
                st.success("✅ Account created! Please switch to the Login tab.")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "already" in msg.lower():
                st.error("❌ Registration failed: that username or email is already taken.")
            else:
                st.error(f"❌ Registration failed: {msg}")

    return False


def render_logout_button(authenticator: stauth.Authenticate | None = None) -> None:
    """Render a logout button in the sidebar.

    If no *authenticator* instance is provided one is created from the
    persisted config.
    """
    if authenticator is None:
        config = load_config()
        authenticator = get_authenticator(config)
    authenticator.logout("Logout", location="sidebar")
