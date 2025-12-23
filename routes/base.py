from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models.connection import db
from models.model import VMRequest

"""
Blueprint per le rotte base accessibili agli utenti autenticati.
"""
base = Blueprint('base', __name__)

"""
Decoratore per la home page
Chiamo la funzione is_authenticated di flask-login per andare a verificare se l'utente é autenticato 
e se no allora lo riporto al login
"""
@base.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('base.dashboard'))
    return redirect(url_for('auth.login'))

"""
Decoratore per la dashboard dell'utente autenticato.
Qui faccio una query al DB per prendere tutte le richieste di VM fatte dall'utente corrente (current_user)
in ordine decrescente di ID (le piu recenti prima)."""
@base.route('/dashboard')
@login_required
def dashboard():
    vm_requests = VMRequest.query.filter_by(user_id=current_user.id).order_by(VMRequest.id.desc()).all()
    return render_template('base/index.html', username=current_user.username, vm_requests=vm_requests)

"""
Decoratore con metodo POST.
Richiesta di una nuova VM da apprte dell'utente autentiocato
semplicemente vado a prendere dal form il vm_type e faccio .strip per rimuovere spazi bianchi
creo l'array con i valid_types e controllo se il vm_type é valido
Lo controllo anche se nel form é un select con opzioni predefinite, ma lo lascio per sicurezza
perche l'utente puo andare a immettere il link della rotta direttamente e mandare un vm_type non valido
Se il vm_type é valido allroa reo una nuova istanza di VMRequest con user_id=current_user.id, vm_type=vm_type e status PENDING
aggiungo la richiesta al DB e faccio commit
poi mostro un flash massage per dire all'utente che la richiesta é stata effettuata
e infine redirigo l'utente alla dashboard
"""
@base.route('/request-vm', methods=['POST'])
@login_required
def request_vm():
    vm_type = request.form.get('vm_type', '').strip()
    valid_types = ['Bronze', 'Silver', 'Gold']
    if vm_type not in valid_types:
        flash('Tipo VM non valido', 'error')
        return redirect(url_for('base.dashboard'))
    vm_request = VMRequest(
        user_id=current_user.id,
        vm_type=vm_type,
        status='PENDING'
    )
    db.session.add(vm_request)
    db.session.commit()
    flash(f'Richiesta VM {vm_type} creata con successo! ID: {vm_request.id}', 'success')
    return redirect(url_for('base.dashboard'))
