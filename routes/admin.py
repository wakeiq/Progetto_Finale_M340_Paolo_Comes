from flask import Blueprint, request, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models.connection import db
from models.model import VMRequest
from routes.auth import user_has_role
from api.proxmox import create_ctx

admin = Blueprint('admin', __name__)

"""
La dashboard mi visualzza tutte le richieste degli utenti,di creazione dei CT.
L'admin puo solo approvare o rifiutare le richieste.
Alll'inerno di questa rotta vado a fare una query al DB per prendere tutte le VM  in 
ordine decrescente di ID (le piu recenti prima).
Poi le passo al template per la visualizzazione.
vm_requests é un array di oggetti VMRequest che contiene tutte le richieste con i loro attributi.
"""
@admin.route('/')
@login_required
@user_has_role('admin')
def dashboard():
    vm_requests = VMRequest.query.order_by(VMRequest.id.desc()).all()
    return render_template('admin/index.html', vm_requests=vm_requests)

"""
La segeuente rotta o decoratore approva la richiesta di creazione del conteiner.
Riceve un argomento in entrata che corrrisponde all'ID della richiesta.
In seguito fa una query al DB per prendere la richiesta con quell'ID, s e non la trova
ritorna un errore 404 perchè la richiesta non esiste e non é stata trovata quindi.
Dopo controllo lo stato della richiesta: 
Se lo stato é PENDING, bene allora procedo con la creazione del CT, quindi chiamo la funzione nel file 
    proxmox.py che si occupa di creare il CT (create_ctx).
Se la creazione va a buon fine, aggiorno lo stato della richiesta a APPROVED e poi salvo le info del CT
(ip, user, password, vmid) nel DB.
Se la creazione fallisce, mostro un messaggio di errore e reindirizzo l'admin alla dashboard.
Se invece lo stato della richiesta all'inizio non era PENDING, allora mosrto ancora un messaggio di errore 
l'approvazione può prendere qualche minuto a causa sia del tmepo di clonazione del template del suo avvio e sia per il tempo
che ci metto per andare a prendere l'IP del container.
(Nella fase di tasting il tempo staimato di attesa é di circa 2-3 minuti, in base al ct richiesto (bronze,silver o gold))
Questa funzione non é stata creata con l'aiuto di DeepSeek, che mi ha aiutato solo nella parte di gestione degli errori, mi ha generato
i flash message e anche la query .get_or_404 che non conoscevo ma che ne ho capito il funzionamento leggendo la documentazione di SQLAlchemy.
"""
@admin.route('/approve/<int:request_id>')
@login_required
@user_has_role('admin')
def approve(request_id):
    vm_request = VMRequest.query.get_or_404(request_id)
    if vm_request.status != 'PENDING':
        flash('Questa richiesta è già stata processata', 'error')
        return redirect(url_for('admin.dashboard'))
    vm_type = vm_request.vm_type
    print(f"Creazione container tipo {vm_type}")
    # chiama la funzione di provisioning rinominata in create_ctx
    result = create_ctx(vm_type, node_index=None)
    if result and result.get('success'):
        vm_request.status = 'APPROVED'
        vm_request.ip = result.get('ip')
        vm_request.vm_user = result.get('vm_user')
        vm_request.vm_password = result.get('vm_password')
        vm_request.vm_id_proxmox = str(result.get('vmid'))
        db.session.commit()
        flash(f'Container approvato e creato con successo! CTID: {result.get("vmid")}', 'success')
    else:
        error_msg = result.get('error', 'Errore sconosciuto') if result else 'Errore connessione Proxmox'
        flash(f'Errore creazione container: {error_msg}', 'error')
    return redirect(url_for('admin.dashboard'))

"""
In questo decoratore vado invece a rifiutare la richiesta di creazione del container.
Semplicemnto prendo la richiesta dal DB e imposto il suo attributo status a REJECTED.
Se la richiesta non é in stato PENDING, mostro un messaggio di errore.
E poi reindirizzo l'admin alla dashboard.
"""
@admin.route('/reject/<int:request_id>')
@login_required
@user_has_role('admin')
def reject(request_id):
    vm_request = VMRequest.query.get_or_404(request_id)
    if vm_request.status != 'PENDING':
        flash('Questa richiesta è già stata processata', 'error')
        return redirect(url_for('admin.dashboard'))
    vm_request.status = 'REJECTED'
    db.session.commit()
    flash('Richiesta rifiutata', 'success')
    
    return redirect(url_for('admin.dashboard'))
