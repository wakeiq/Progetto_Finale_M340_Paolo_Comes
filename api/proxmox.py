import requests
import urllib3
import os
import time
from dotenv import load_dotenv

load_dotenv()
#disattivo warning per le richieste https senza un certifcato valido
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#salvo in un array gli ip statici dei nodi 1, 2 e 10 di Proxmox
#inoltre memorizza anche la porta di defualt di Proxmox per poter fare connessioni API
#Nella variabile token_id vado a prendere l'id del token di accesso alle API di Proxmox che salvo nel file .env
#e nella variabile token_secret prendo la secret del token di accesso alle API di Proxmox. Anche quello lo savlo nel .env
#Salvo gli hostname dei nodi del cluster di Proxmox, e memorizzo anche lo storage dove poi verranno clonati i conteiners
#IDS dei template che ho creato in precedenza per i conteinrs Gold, Silver e Bronze
#Nell'utlimo creo un dizionario per mappare il tipo di VM al nodo corretto
PROXMOX_NODE_IPS = ['192.168.56.15', '192.168.56.16', '192.168.56.17']
PROXMOX_PORT = 8006
PROXMOX_API_TOKEN_ID = os.getenv('PROXMOX_TOKEN_ID')
PROXMOX_API_TOKEN_SECRET = os.getenv('PROXMOX_TOKEN_SECRET')
PROXMOX_NODE_NAMES = ['px1', 'px2', 'px10']
PROXMOX_STORAGE_NAME = 'local-lvm'
PROXMOX_TEMPLATE_VMID_LIST = [2112, 2111, 2110]
VM_TYPE_TO_NODE_INDEX = {'Gold': 0, 'Silver': 1, 'Bronze': 2}

"""
Ottengo l'URL di base per poter fare le richieste all'API di proxmox
"""
def get_proxmox_url(host):
    return f'https://{host}:{PROXMOX_PORT}/api2/json'

"""
Ritorno l'header con il token id e il token secrete per poter autenticarmi al API
"""
def get_auth_headers():
    return {'Authorization': f'PVEAPIToken={PROXMOX_API_TOKEN_ID}={PROXMOX_API_TOKEN_SECRET}'}

"""
Ritorno il prossimo CTID disponibile per un container su un nodo specifico
nel try catch provo a fare una chiamata di tipo GET perottenere la lista di tutti i containers presenti nel nodo
dopodiche nella variabile data di tipo JSON memorizzo la lista 
di tutti i containers presenti. Infatti vado a prendere la chiave data
dal JSON che ricevo, e se data non esiste assegno di default uan lista vuota per evitare crash
Nella variabile existing_ids vado a creare uan lista di tutti gli ID numerici 
dei containers esistenti, escludendo l'ID del template
infatti dico che che per ogni elemnento 'ct' dentro data prendi ct['vmid'] 
e convertimelo in INT, ma solo se il VMID non é uguale al template_id
altrimenti entrerebbero in conflitto i due conteiners e non riuscere a crearli.
Se ottengo la lista senza problemi, allora dalla lista existing_ids prendo l'ultimo ID
Quindi quello massimo, e ci soommo 1 per ottenere l'ID sucessivo, ovvero libero.
All'ultimo existing_ids aggiungo 99 perché se non ci sono containers esistenti, il max mi ritorna errore
e quindi in quel caso parto da 100 come primo ID libero.
Se queste operazioni vanno in errore, allora la funtione ritorna None
"""
def get_id(node_index):
    host_ip = PROXMOX_NODE_IPS[node_index]
    node_name = PROXMOX_NODE_NAMES[node_index]
    template_vmid = PROXMOX_TEMPLATE_VMID_LIST[node_index]

    url = f'{get_proxmox_url(host_ip)}/nodes/{node_name}/lxc'
    try:
        r = requests.get(url, headers=get_auth_headers(), verify=False)
        data = r.json().get('data', [])
        existing_ids = [int(ct['vmid']) for ct in data if int(ct['vmid']) != template_vmid]
        return max(existing_ids + [99]) + 1
    except:
        return None

"""
Nella firma della funzione prendo come input l'indice del nodo e il CTID (id numerico del container)
 da avviare
Risoluzione del node.
PROXMOX_HOSTS --> lista di IP
PROXMOX_NODES --> lista di nomi nodo
Poi costruisco chiamata API di tipo POST per dire che lo stato del conteiner é start
Infine nel try catch provo a fare la chiamata POST e se lo status code é 200 ritorno True
altrimenti ritorno false
"""
def start_ct(node_index, ctid):
    host_ip = PROXMOX_NODE_IPS[node_index]
    node_name = PROXMOX_NODE_NAMES[node_index]
    url = f'{get_proxmox_url(host_ip)}/nodes/{node_name}/lxc/{ctid}/status/start'
    try:
        r = requests.post(url, headers=get_auth_headers(), verify=False)
        return r.status_code == 200
    except:
        return False

"""
La funzione tenta di recuperare l'indirizzo IPv4 di un container LXC
interrogando periodicamente le API REST.
Parametri in entrata che acetta la funzione:
- host: IP o hostname del nodo Proxmox
- node: nome del nodo Proxmox
- ctid: ID numerico del container LXC
- timeout: tempo massimo (in secondi) entro cui tentare il recupero dell'IP che di default è settato a 120
La funzione interroga ciclicamente i seguenti endpoint:
- /nodes/{node}/lxc/{ctid}/interfaces
- /nodes/{node}/lxc/{ctid}/status/network ---> questo endpoint non esiste in realtà nel API proxmox 9.0.3
ma fa parte di una versione predente, ma comque il codice funziona.
Il polling continua finché:
- viene trovato un indirizzo IPv4 valido che non sia 127.0.0.1 e che non sia un indirizzo di loopback
- oppure scade il timeout (120s)
Ad ogni iterazione:
- viene effettuata una chiamata GET autenticata
- se la risposta è valida, viene analizzato ricorsivamente il JSON di risposta
- vengono estratti tutti gli indirizzi IPv4 trovati
- viene restituito l'IP migliore secondo le seguenti priorità:
  IP privato non loopback
  IP pubblico non loopback
  IP loopback (fallback)
La funzione è pensata come alternativa al cloud-init,
siccome quando ho oprovato ad installarlo mi dava altri problemi nell'impostare manualmente un ip statico e anche
nel andarlo a riprendere tramite la richiesta API.
Il timeout consente di attendere che il container completi l'avvio
e ottenga un IP tramite DHCP.
Se allo scadere del timeout non viene trovato alcun IP, la funzione ritorna None.
La funzione è stata implementata grazie a ChatGPT, dopo diversi sforzi e test nel provarci da solo.
"""
def get_ip(host, node, ctid, timeout=120):
    import os
    import re
    import time
    import requests
    PROXMOX_DEBUG = os.getenv("PROXMOX_DEBUG")
    endpoints = [
        f"{get_proxmox_url(host)}/nodes/{node}/lxc/{ctid}/interfaces",
        f"{get_proxmox_url(host)}/nodes/{node}/lxc/{ctid}/status/network",
    ]
    ipv4_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    def is_private(ip):
        return (
            ip.startswith("10.")
            or ip.startswith("192.168.")
            or bool(re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", ip))
        )
    def is_bad(ip):
        return ip.startswith("127.") or ip.startswith("169.254.")
    def extract_ips(obj):
        found = []
        if isinstance(obj, dict):
            for v in obj.values():
                found += extract_ips(v)
        elif isinstance(obj, list):
            for v in obj:
                found += extract_ips(v)
        elif isinstance(obj, str):
            m = ipv4_re.search(obj)
            if m:
                found.append(m.group(0))
        return found
    def pick_best(ips):
        for ip in ips:
            if not is_bad(ip) and is_private(ip):
                return ip
        for ip in ips:
            if not is_bad(ip):
                return ip
        return ips[0] if ips else None
    start = time.time()
    while time.time() - start < timeout:
        for url in endpoints:
            try:
                r = requests.get(url, headers=get_auth_headers(), verify=False)
                if r.status_code != 200:
                    continue
                data = r.json().get("data", {})
            except Exception:
                continue
            ips = extract_ips(data)
            ip = pick_best(ips)
            if ip:
                return ip
            if PROXMOX_DEBUG:
                try:
                    print(f"[PROXMOX DEBUG] {url} -> {r.json()}")
                except Exception:
                    print(f"[PROXMOX DEBUG] {url} -> {r.text}")
        time.sleep(3)
    return None
"""
Nella firma della funzione prendo come input:
- node_index: indice numerico del nodo Proxmox da utilizzare
- new_ctid: ID numerico del nuovo container da creare
- vm_type: tipo di container
Preparo poi i parametri per la clonazione, quindi:
- newid: ID del nuovo container che andro a clonare
- hostname: nome del container
- storage: storage Proxmox su cui creare il container
- full: ovvero clone completo
Costruisco per avvia il processo di clonazione del template.
Nel blocco try catch vado a:
- eseguire la eicheista di tipo POST per clonare il container
- se lo status code non è 200:
  - ritorno errore con il contenuto della risposta
Se la chiamata va a buon fine:
- estraggo l’UPID (task ID) dalla risposta JSON
- entro in un ciclo di polling che:
  - interroga periodicamente lo stato del task
  - controlla se il task è terminato
Per ogni controllo:
- se lo stato del task è 'stopped':
  - se exitstatus è 'OK' la clonazione è riuscita
  - altrimenti ritorno errore con lo stato di uscita
- se il tempo supera il timeout massimo:
  - ritorno errore di timeout
Terminata con successo la clonazione:
    - avvio il container chiamando la funzione start_ct
- se l’avvio fallisce ritorno errore
Dopo l’avvio del container:
- provo a recuperare l’indirizzo IP reale del container
    usando la funzione get_ip
- attendo fino a un timeout massimo
e se poi tutto va a buon fine:
- ritorno un dizionario con:
  - success = True
  - vmid del container
  - indirizzo IP assegnato
  - credenziali di accesso (utente e password)
In caso di errore o di qalsiasi altra eccezione:
- catturo l’errore
- ritorno un dizionario success = False con il messaggio di errore
La segeunte funzione é stata creata con l'aiuto di ChatGPT, che mi ha suggerito la struttura e i passaggi principali
per implementare la clonazione di un container LXC su Proxmox tramite API.
"""
def clone_container(node_index, new_ctid, vm_type):
    host_ip = PROXMOX_NODE_IPS[node_index]
    node_name = PROXMOX_NODE_NAMES[node_index]
    template_vmid = PROXMOX_TEMPLATE_VMID_LIST[node_index]
    params = {
        'newid': new_ctid,
        'hostname': f'ct-{vm_type.lower()}-{new_ctid}',
        'storage': PROXMOX_STORAGE_NAME,
        'full': 1
    }
    try:
        url = f'{get_proxmox_url(host_ip)}/nodes/{node_name}/lxc/{template_vmid}/clone'
        r = requests.post(url, headers=get_auth_headers(), data=params, verify=False)
        if r.status_code != 200:
            return {'success': False, 'error': r.text}
        upid = r.json()['data']
        timeout = 300
        start_time = time.time()
        while True:
            url_task = f'{get_proxmox_url(host_ip)}/nodes/{node_name}/tasks/{upid}/status'
            r_task = requests.get(url_task, headers=get_auth_headers(), verify=False)
            task_data = r_task.json().get('data', {})
            if task_data.get('status') == 'stopped':
                if task_data.get('exitstatus') == 'OK':
                    break
                return {'success': False, 'error': f"Clone fallito, exitstatus={task_data.get('exitstatus')}"}
            if time.time() - start_time > timeout:
                return {'success': False, 'error': 'Timeout clone'}
            time.sleep(2)
        if not start_ct(node_index, new_ctid):
            return {'success': False, 'error': 'Avvio container fallito'}
        ip_real = get_ip(host_ip, node_name, new_ctid, timeout=180)
        return {
            'success': True,
            'vmid': new_ctid,
            'ip': ip_real,
            'vm_user': 'root',         
            'vm_password': 'Password&1'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
"""
funzione che crea il conteiner LXC su proxmox
Nella firma della funzione prendo come input:
- vm_type: tipo di container da creare
e poi il nodo index che di difeault é none perche mi dava problemi.
Se l'idex del nodo é none allroa riotrno un errore che il tipo di VM non é valido
Altrimenti proseguo e chiamo la funzione per ottenere il prossimo CTID libero
Se non riesco ad ottenere il CTID ritorno errore
Altrimenti chiamo la funzione clone_container per procedere con la clonazione del container
Ritrono il risultato della clonazione quindi:
        return {
            'success': True,
            'vmid': new_ctid,
            'ip': ip_real,
            'vm_user': 'root',         
            'vm_password': 'Password&1'
        }
        oppure False + errore
"""
def create_ctx(vm_type, node_index=None):
    if node_index is None:
        node_index = VM_TYPE_TO_NODE_INDEX.get(vm_type)
        if node_index is None:
            return {'success': False, 'error': f'Tipo VM {vm_type} non valido'}

    ctid = get_id(node_index)
    if ctid is None:
        return {'success': False, 'error': 'Impossibile ottenere CTID'}

    return clone_container(node_index, ctid, vm_type)
