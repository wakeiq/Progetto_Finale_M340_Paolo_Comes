# Gestione VM con Flask, SQLAlchemy e Proxmox

Progetto Flask con SQLAlchemy per gestire richieste di container LXC con integrazione API Proxmox.

## Descrizione

Questo progetto permette agli utenti di richiedere container LXC (Bronze, Silver, Gold) e agli amministratori di approvare le richieste. Quando una richiesta viene approvata, viene automaticamente creato un container su Proxmox tramite API.

## Struttura del Progetto

```
hello_world_blueprint/
├── app.py                 # Applicazione Flask principale
├── models/
│   ├── connection.py      # Configurazione SQLAlchemy
│   └── model.py           # Modelli User e VMRequest
├── api/
│   └── proxmox.py         # Integrazione API Proxmox per container LXC
├── routes/
│   ├── auth.py           # Route per autenticazione (Flask-Login)
│   ├── base.py           # Route per dashboard utente
│   └── admin.py          # Route per dashboard admin
├── templates/
│   ├── auth/
│   │   └── login.html    # Pagina di login
│   ├── base/
│   │   └── index.html    # Dashboard utente
│   └── admin/
│       └── index.html    # Dashboard admin
├── labo.db               # Database SQLite (creato automaticamente)
├── requirements.txt      # Dipendenze Python
└── env.example           # Esempio file .env
```

## Installazione
1. **Installa le dipendenze:**
   ```bash
   git clone https://github.com/wakeiq/Progetto_Finale_M340_Paolo_Comes.git
   cd Progetto_Finale_M340_Paolo_Comes
   python -m venv venv
   pip install -r requirements.txt
   ```

2. **Crea il file .env:**
   
   Copia `env.example` in `.env` e modifica i valori:
   ```bash
   cp env.example .env
   ```
   
   Modifica il file `.env` con le tue configurazioni, TOKEN ID e TOKEN SECRET LE RICEVERAI PER EMAIL:
   ```env
   HOST=localhost
   PORT=5000
   SECRET_KEY=chiave-segreta-per-sessioni-cambiala-in-produzione
   SQLALCHEMY_DATABASE_URI=sqlite:///labo.db
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=password
   PROXMOX_TOKEN_ID=your-token-id@realm
   PROXMOX_TOKEN_SECRET=your-token-secret
   ```

3. **Configura Proxmox:**
   
   Modifica anche la variabile in `api/proxmox.py` se necessario:
   ```python
   PROXMOX_HOSTS = ['192.168.1.17', '192.168.1.18', '192.168.1.19']
   ```

4. **Inizializza il database:**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```
   
   Oppure semplicemente avvia l'app (il database viene creato automaticamente):
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

5. **Avvia l'applicazione:**
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

6. **Apri il browser:**
   ```
   http://192.168.56.20:5000
   ```

## Credenziali di Default

All'avvio viene creato automaticamente un utente admin se non esiste:

- **Email:** Valore da `ADMIN_EMAIL` nel file `.env` (default: `admin@example.com`)
- **Password:** Valore da `ADMIN_PASSWORD` nel file `.env` (default: `password`)
- **Ruolo:** `admin`

## Funzionalità

### Autenticazione (Flask-Login)

- Login con username o email
- Sessioni persistenti con Flask-Login
- Decoratori per proteggere le route
- Decoratore `@user_has_role('admin')` per route admin

### Flusso Utente

1. **Login:**
   - L'utente accede alla pagina di login (`/login`)
   - Inserisce username/email e password
   - Viene reindirizzato alla dashboard

2. **Dashboard Utente:**
   - Visualizza tutte le sue richieste container
   - Può richiedere un nuovo container scegliendo tra:
     - **Bronze:** 1 core, 500MB RAM
     - **Silver:** 2 core, 2GB RAM
     - **Gold:** 3 core, 4GB RAM
   - Le richieste vengono salvate con stato `PENDING`

3. **Visualizzazione Stato:**
   - **PENDING:** Richiesta in attesa di approvazione
   - **APPROVED:** Richiesta approvata, mostra IP, username e password del container
   - **REJECTED:** Richiesta rifiutata

### Flusso Admin

1. **Accesso Dashboard Admin:**
   - L'admin accede a `/admin`
   - Visualizza tutte le richieste di tutti gli utenti

2. **Gestione Richieste:**
   - Per ogni richiesta `PENDING` può:
     - **Approva:** Chiama l'API Proxmox per creare il container LXC
     - **Rifiuta:** Rifiuta la richiesta senza creare il container

3. **Approva Richiesta:**
   - Quando l'admin approva una richiesta:
     1. Viene chiamata l'API Proxmox
     2. Viene clonato un container LXC dal template
     3. Vengono configurate CPU e RAM in base al tipo
     4. Il container viene avviato
     5. Vengono salvati nel database:
        - CTID Proxmox
        - IP del container
        - Username e password del container

## Database (SQLAlchemy)

Il database SQLite (`labo.db`) viene creato automaticamente all'avvio.

### Modelli

**User:**
- `id` - ID univoco
- `username` - Nome utente (unico)
- `email` - Email (unica)
- `password_hash` - Password hashata con Werkzeug
- `role` - Ruolo (`user` o `admin`)
- Relazione con `VMRequest`

**VMRequest:**
- `id` - ID univoco
- `user_id` - Foreign key a User
- `vm_type` - Tipo container (`Bronze`, `Silver`, `Gold`)
- `status` - Stato (`PENDING`, `APPROVED`, `REJECTED`)
- `ip` - IP del container (se approvato)
- `vm_user` - Username del container (se approvato)
- `vm_password` - Password del container (se approvato)
- `vm_id_proxmox` - CTID Proxmox (se approvato)

## Integrazione API Proxmox

Il modulo `api/proxmox.py` gestisce tutte le chiamate all'API Proxmox per container LXC.

### Funzionalità

1. **get_id():** Ottiene il prossimo CTID disponibile
2. **clone_container():** Clona un container LXC dal template
3. **configure_container_resources():** Configura CPU e RAM del container
4. **start_ct():** Avvia il container
5. **create_ctx():** Funzione principale che crea un container completo

### Autenticazione

L'autenticazione avviene tramite token API Proxmox. Il token viene passato negli header HTTP:

```
Authorization: PVEAPIToken=TOKEN_ID=TOKEN_SECRET
```

### Note

- Le richieste HTTPS a Proxmox vengono fatte con `verify=False` (per certificati self-signed)
- L'IP del container viene generato in modo semplificato (in produzione usare l'API per ottenere l'IP reale)
- La password del container è impostata di default a `changeme123` (da cambiare in produzione)

## Tipologie di Container

| Tipo   | CPU  | RAM      | Memoria |      
|--------|------|----------|---------|
| Bronze | 1    | 500 MB   | 8 GB    |
| Silver | 2    | 2 GB     | 16 GB   |
| Gold   | 3    | 4 GB     | 28 GB   |

## Tecnologie Utilizzate

- **Flask:** Framework web
- **SQLAlchemy:** ORM per database
- **Flask-Login:** Gestione autenticazione
- **Flask-Migrate:** Migrazioni database
- **python-dotenv:** Gestione variabili d'ambiente
- **requests:** Chiamate API Proxmox
- **Bootstrap 5:** Framework CSS per interfaccia grafica (via CDN)

## Sviluppo

### Struttura del Codice

- **Modelli SQLAlchemy:** `models/model.py`
- **Autenticazione separata:** `routes/auth.py`
- **Blueprint organizzati:** Route separate per base, admin e auth
- **API Proxmox:** Modulo separato in `api/proxmox.py`

### File Principali

- `app.py`: Configurazione Flask, SQLAlchemy, Flask-Login, registrazione blueprint
- `models/model.py`: Modelli User e VMRequest con SQLAlchemy
- `routes/auth.py`: Login, logout, decoratori per ruoli
- `routes/base.py`: Dashboard utente, richiesta container
- `routes/admin.py`: Dashboard admin, approva/rifiuta richieste
- `api/proxmox.py`: Funzioni per chiamare API Proxmox (container LXC)

## Troubleshooting

### Errore connessione Proxmox

Se vedi errori di connessione a Proxmox:
1. Verifica che gli host siano raggiungibili
2. Controlla che il token API sia corretto nel file `.env`
3. Verifica che i template container esistano sui nodi specificati
4. Controlla i log nella console per dettagli sull'errore

### Database non creato

Se il database non viene creato:
- Verifica i permessi di scrittura nella directory
- Controlla che SQLAlchemy sia installato correttamente
- Verifica il percorso nel file `.env`

### Errori di autenticazione

Se hai problemi con il login:
- Verifica che l'utente admin sia stato creato (controlla i log all'avvio)
- Controlla che le password siano corrette nel file `.env`
- Verifica che Flask-Login sia configurato correttamente

## Note di Sicurezza

**IMPORTANTE:** Questo progetto è per scopi didattici/demo.

Per un ambiente di produzione:
- Usa password più sicure
- Cambia `SECRET_KEY` nel file `.env` con una chiave casuale sicura
- Usa certificati SSL validi per Proxmox

## Licenza

Progetto educativo - uso libero.


