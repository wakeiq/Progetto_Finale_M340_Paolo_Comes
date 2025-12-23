"""
Route per autenticazione con Flask-Login
"""
from flask import Blueprint
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import flash
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from flask import abort
from models.connection import db
from models.model import User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET'])
def login():
    """
    Mostra la pagina di login
    """
    return render_template('auth/login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    """
    Gestisce il login POST
    """
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    remember = True if request.form.get('remember') else False
    
    if not username or not password:
        flash('Inserisci username e password', 'error')
        return redirect(url_for('auth.login'))
    
    # Cerca utente per username o email
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    # Verifica se l'utente esiste e la password è corretta
    if not user or not user.check_password(password):
        flash('Username o password errati', 'error')
        return redirect(url_for('auth.login'))
    
    # Login riuscito
    login_user(user, remember=remember)
    
    # Reindirizza in base al ruolo
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('base.dashboard'))

@auth.route('/signup', methods=['GET'])
def signup():
    """
    Mostra la pagina di registrazione
    """
    return render_template('auth/signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():
    """
    Gestisce la registrazione POST
    """
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')
    
    # Validazione
    if not username:
        flash('Username obbligatorio', 'error')
        return redirect(url_for('auth.signup'))
    
    if not email:
        flash('Email obbligatoria', 'error')
        return redirect(url_for('auth.signup'))
    
    if not password:
        flash('Password obbligatoria', 'error')
        return redirect(url_for('auth.signup'))
    
    if password != password_confirm:
        flash('Le password non corrispondono', 'error')
        return redirect(url_for('auth.signup'))
    
    if len(password) < 4:
        flash('La password deve essere di almeno 4 caratteri', 'error')
        return redirect(url_for('auth.signup'))
    
    # Verifica se username o email esistono già
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        flash('Username o email già esistente', 'error')
        return redirect(url_for('auth.signup'))
    
    # Crea nuovo utente (sempre ruolo 'user', non admin)
    new_user = User(
        username=username,
        email=email,
        role='user'  # Sempre utente normale
    )
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    
    flash('Registrazione completata! Ora puoi fare login', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    """
    Logout utente
    """
    logout_user()
    flash('Logout effettuato con successo', 'success')
    return redirect(url_for('auth.login'))

def user_has_role(*role_names):
    """
    Decorator per verificare che l'utente abbia uno dei ruoli specificati
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Devi essere autenticato per accedere a questa pagina.", 'error')
                return redirect(url_for('auth.login'))
            if not any(current_user.has_role(role) for role in role_names):
                flash("Non hai il permesso per accedere a questa pagina.", 'error')
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

