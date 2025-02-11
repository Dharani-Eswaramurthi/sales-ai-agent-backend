import dns.resolver
from fastapi import HTTPException

def identify_smtp_server(email: str) -> tuple:
    # Extract the domain from the email address.
    try:
        domain = email.split('@')[-1].lower()
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Mapping from substrings (found in MX records) to SMTP server settings.
    # For example, if the MX record contains 'google.com' then we assume the provider is Gmail.
    known_mx_map = {
        'google.com': ('smtp.gmail.com', 587),
        'yahoo.com': ('smtp.mail.yahoo.com', 587),
        'outlook.com': ('smtp.office365.com', 587),
        'hotmail.com': ('smtp.office365.com', 587),
        'hostinger.com': ('smtp.hostinger.com', 587),
        # You can add additional keys as needed.
    }
    
    # Attempt to retrieve the MX records for the domain.
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Unable to resolve MX record for domain '{domain}': {e}"
        )
    
    # Check each MX record against the known keys.
    for mx in mx_records:
        mx_name = str(mx.exchange).rstrip('.').lower()
        for key, smtp_info in known_mx_map.items():
            if key in mx_name:
                return smtp_info
    
    # If no known key is found in the MX records, return a default SMTP server.
    return ("smtpout.secureserver.net", 587)

# Example usage:
smtp_server, smtp_port = identify_smtp_server("dharni@heuro.in")
print(smtp_server, smtp_port)
