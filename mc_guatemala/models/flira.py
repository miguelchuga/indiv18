# -*- encoding: utf-8 -*-
import json
import xmlrpc.client

url = "http://localhost:8069" # Cambia esto por la URL de tu instancia de Odoo
db = "doce_domini" # Cambia esto por el nombre de tu base de datos en Odoo
username = "admin@marcos.do" # Cambia esto por tu nombre de usuario en Odoo
password = "Mnbvcxz" # Cambia esto por tu contraseña en Odoo

common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(url))
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy("{}/xmlrpc/2/object".format(url))

# Buscando contactos
domain = [("id", "=", 1042), ("x_tipo_publicacion", "=", 'fbinsta')]
fields = ["subject", "contact_list_ids", "body_html"]

contacts = models.execute_kw(
    db, uid, password,
    "mailing.mailing", "search_read",
    [domain, fields]
)

print(json.dumps(contacts, indent=4))
