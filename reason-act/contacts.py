contacts = {
    "valentin": "me@valenradovich.tech",
    #"mom": "mom@example.com",
    #"dad": "dad@example.com",
}

def get_contact_email(name):
    return contacts.get(name.lower(), None)
