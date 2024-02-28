import config

if config.pass_scan_type == 0:
    import ajax_passwords
else:
    import gateway_passwords

def start_passwords_scan():
    if config.pass_scan_type == 0:
        ajax_passwords.start_passwords_scan()
    else:
        gateway_passwords.start_passwords_scan()

def is_pooling():
    if config.pass_scan_type == 0:
        return ajax_passwords.is_pooling()
    else:
        return gateway_passwords.is_pooling()

def clear():
    if config.pass_scan_type == 0:
        ajax_passwords.clear()
    else:
        gateway_passwords.clear()

def join():
    if config.pass_scan_type == 0:
        ajax_passwords.join()
    else:
        gateway_passwords.join()

def set_api_url(url):
    if config.pass_scan_type == 0:
        ajax_passwords.api_path = url

def set_map_end(val):
    if config.pass_scan_type == 0:
        ajax_passwords.map_end = val
    else:
        gateway_passwords.map_end = val
# крутой модуль, да?