import re
import smtplib
import dns.resolver
from concurrent.futures import ThreadPoolExecutor

def is_valid_email_format(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def get_mx_records(domain):
    try:
        # Use a custom resolver with public DNS and increased timeout
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '1.1.1.1']  # Google and Cloudflare DNS
        resolver.timeout = 10
        resolver.lifetime = 10
        mx_records = resolver.resolve(domain, 'MX')
        return [record.exchange.to_text() for record in mx_records]
    except dns.resolver.NoAnswer:
        raise ValueError(f"No MX records found for domain: {domain}")
    except Exception as e:
        raise ValueError(f"Error fetching MX records: {e}")

def verify_email_smtp(email, mx_host, from_address="test@example.com"):
    try:
        with smtplib.SMTP(mx_host, timeout=10) as server:
            server.helo("example.com")
            server.mail(from_address)
            code, _ = server.rcpt(email)
            return code == 250
    except Exception:
        return False

def verify_email_parallel(email, mx_records):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(verify_email_smtp, email, mx) for mx in mx_records]
        for future in futures:
            if future.result():
                return True
    return False

def generate_email_combinations(first_name, last_name, domain):
    first_name = first_name.lower()
    last_name = last_name.lower()
    return [
        # Most common formats
        f"{first_name}.{last_name}@{domain}",    # john.doe@example.com
        f"{first_name}{last_name}@{domain}",     # johndoe@example.com
        f"{first_name}@{domain}",                 # john@example.com
        f"{first_name}_{last_name}@{domain}",    # john_doe@example.com
        f"{first_name[0]}{last_name}@{domain}",  # jdoe@example.com
        f"{first_name}{last_name[0]}@{domain}",  # john.d@example.com

        # Variations with separators
        f"{first_name}-{last_name}@{domain}",    # john-doe@example.com
        f"{first_name[0]}.{last_name}@{domain}", # j.doe@example.com
        f"{first_name[0]}_{last_name}@{domain}", # j_doe@example.com
        
        # Reverse order
        f"{last_name}.{first_name}@{domain}",    # doe.john@example.com
        f"{last_name}.{first_name[0]}@{domain}",  #doe.j@example.com
        f"{last_name}_{first_name}@{domain}",    # doe_john@example.com
        f"{last_name}-{first_name}@{domain}",    # doe-john@example.com
        f"{last_name}{first_name}@{domain}",     # doejohn@example.com
        f"{last_name}{first_name[0]}@{domain}",  # doej@example.com
        f"{last_name[0]}{first_name}@{domain}",  # djohn@example.com
        f"{last_name[0]}.{first_name}@{domain}", # d.john@example.com
        f"{last_name[0]}_{first_name}@{domain}", # d_john@example.com

        # Other potential formats
        f"{first_name}{last_name[0]}@{domain}",  # johndoe@example.com (with middle initial)
        f"{first_name[0]}{last_name[0]}@{domain}",# jd@example.com (initials)
        
        # Additional variations that may be used:
        f"{first_name}.{last_name[0]}@{domain}",  # john.d@example.com (with last initial)
        f"{last_name}{first_name}@{domain}",      # doejohn@example.com (reverse)
        
        # Including numbers (for cases where names are common)
        f"{first_name}{last_name}1@{domain}",     # johndoe1@example.com
        f"{first_name}{last_name}123@{domain}",   # johndoe123@example.com
        
        # Adding middle initials or names if applicable (if provided as an argument)
    ]

def find_valid_email(first_name, last_name, domain):
    try:
        combinations = generate_email_combinations(first_name, last_name, domain)
        mx_records = get_mx_records(domain)

        if not mx_records:
            raise ValueError(f"No MX records found for domain: {domain}")

        print(f"Found MX records for {domain}: {mx_records}")

        for email in combinations:
            if not is_valid_email_format(email):
                print(f"Skipping invalid email format: {email}")
                continue

            print(f"Checking deliverability for: {email}")
            if verify_email_parallel(email, mx_records):
                print(f"Valid email found: {email}")
                return email

        print("No valid email found.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Example Usage
# if __name__ == "__main__":
#     first_name = input("Enter First Name: ")
#     last_name = input("Enter Last Name: ")
#     domain = input("Enter Domain (e.g., example.com): ")

#     if first_name and last_name and domain:
#         print("Searching for a valid email...")
#         valid_email = find_valid_email(first_name, last_name, domain)
#         if valid_email:
#             print(f"Deliverable email: {valid_email}")
#         else:
#             print("No deliverable email found.")
#     else:
#         print("Please provide all inputs (First Name, Last Name, Domain).")
