# auth.py
import os
from flask import url_for, redirect, session, request, flash, jsonify
from authlib.integrations.flask_client import OAuth
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # If request expects JSON (fetch / AJAX)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
                return jsonify({
                    "error": "not_authenticated",
                    "message": "You are not logged in"
                }), 401

            # Normal browser request
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_oauth(app):
    """
    Create OAuth(app) and register the Google provider.
    Returns (oauth, google).
    """
    oauth = OAuth(app) # OAuth is a way to safely let users login using Google without handling their passwords yourself
    google = oauth.register( # Then you told OAuth: Hey OAuth
    
    name='google', # register Google as a login provider, and here’s my...
    client_id=app.config["GOOGLE_CLIENT_ID"], # client_id
    client_secret=app.config["GOOGLE_CLIENT_SECRET"], # a secret password only your app and Google know 
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration', # Google OpenID configuration URL (this tells your app where to send users to login)
    client_kwargs={'scope': 'openid email profile'} # meaning what user info you want to access.
    )
    return oauth, google

def register_auth_routes(app, google):
    """
    Attach /login, /logout and /auth/callback routes to the Flask `app`.
    Call this after init_oauth() in your main app.
    """
    @app.route('/login')
    def login():
        redirect_uri = url_for('authorized', _external=True)
        return google.authorize_redirect(redirect_uri) #User clicks Login → /login → Google login page → /auth/callback

    @app.route('/logout')
    def logout():
        session.pop('user', None)
        session.pop('google_token', None)
        return redirect(url_for('api.index'))

    @app.route('/auth/callback')
    def authorized():
        token = google.authorize_access_token()
        if token is None:
            return 'Access denied: reason={} error={}'.format(
                request.args.get('error_reason'),
                request.args.get('error_description')
            ) # If token is missing (maybe user said "No" or an error happened)
        session['google_token'] = token
        user_info = google.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
        session['user'] = user_info
        email = user_info.get('email')

        if not email or not email.endswith('study.iitm.ac.in'):
            flash('Access denied: unauthorized email domain. Please login again with a valid email address.')
            session.pop('user', None)
            session.pop('google_token', None)
            return redirect(url_for('api.index'))

        session['user'] = user_info
        return redirect(url_for('api.index'))