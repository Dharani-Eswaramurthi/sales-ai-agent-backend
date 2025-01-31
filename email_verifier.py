import os
import re
import smtplib
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SENDGRID_SMTP_SERVER = "smtp.sendgrid.net"
SENDGRID_PORT = 587
VERIFIED_DOMAIN = "greenvy.store"  # Your authenticated domain
FROM_ADDRESS = f"contact@{VERIFIED_DOMAIN}"  # Dedicated verification address
MAX_WORKERS = 2  # Conservative concurrency
REQUEST_DELAY = 1  # Seconds between attempts
MAX_RETRIES = 2  # Per-email retry attempts

def is_valid_email_format(email: str) -> bool:
    """Validate email format with strict regex"""
    email_regex = r'^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$'
    return re.fullmatch(email_regex, email) is not None

def generate_email_combinations(first_name: str, last_name: str, domain: str) -> list:
    """Generate prioritized email combinations with likelihood ranking"""
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    domain = domain.lower().strip()
    
    return [
        f"{first}@{domain}",             # john@
        # Highest probability formats (85% coverage)
        f"{first}.{last}@{domain}",      # john.doe@
        # f"{first[0]}{last}@{domain}",    # jdoe@
        f"{first}{last}@{domain}",       # johndoe@
        
        # Common professional formats
        f"{first}_{last}@{domain}",      # john_doe@
        f"{last}.{first}@{domain}",      # doe.john@
        # f"{first[0]}.{last}@{domain}",   # j.doe@
        
        # Less common but valid formats
        f"{first}-{last}@{domain}",      # john-doe@
        # f"{last}{first[0]}@{domain}",    # doej@
        # f"{first}{last[0]}@{domain}",    # john.d@
    ]

def verify_email_smtp(email: str) -> bool:
    """Verify email using SendGrid's SMTP (returns boolean only)"""
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.error("SendGrid API key not found in environment variables")
        return False

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Attempting to verify {email} (attempt {attempt+1})")
            with smtplib.SMTP(SENDGRID_SMTP_SERVER, SENDGRID_PORT, timeout=15) as server:
                server.starttls()
                server.login("apikey", api_key)
                
                server.ehlo_or_helo_if_needed()
                server.mail(FROM_ADDRESS)
                code, message = server.rcpt(email)
                server.rset()
                
                logger.info(f"SMTP response for {email}: {code} - {message.decode()}")
                
                if code == 250:
                    return True
                if code == 450:
                    continue
                return False

        except smtplib.SMTPServerDisconnected:
            logger.warning(f"SMTP server disconnected (attempt {attempt+1})")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Error verifying {email}: {str(e)}")
            break

    return False

def find_valid_email(first_name: str, last_name: str, domain: str) -> str | None:
    """Find valid email based on first successful verification"""
    if not all([first_name, last_name, domain]):
        logger.error("Missing required input parameters")
        return None

    if not is_valid_email_format(f"test@{domain}"):
        logger.error(f"Invalid domain format: {domain}")
        return None

    candidates = generate_email_combinations(first_name, last_name, domain)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all candidates for verification
        future_to_email = {
            executor.submit(verify_email_smtp, email): email
            for email in candidates
            if is_valid_email_format(email)
        }

        # Process results in completion order (not priority order)
        for future in as_completed(future_to_email):
            email = future_to_email[future]
            try:
                if future.result():
                    logger.info(f"First accepted email: {email}")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return email
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                logger.error(f"Verification failed for {email}: {str(e)}")

    logger.info("No deliverable email found")
    return None

# if __name__ == "__main__":
#     # Example usage with input validation
#     try:
#         first_name = input("Enter First Name: ").strip()
#         last_name = input("Enter Last Name: ").strip()
#         domain = input("Enter Domain (e.g., example.com): ").strip()

#         if not all([first_name, last_name, domain]):
#             raise ValueError("All fields are required")

#         print("Searching for valid email...")
#         valid_email = find_valid_email(first_name, last_name, domain)
        
#         if valid_email:
#             print(f"Validated email: {valid_email}")
#         else:
#             print("No valid email found")

#     except KeyboardInterrupt:
#         print("\nOperation cancelled by user")
#     except Exception as e:
#         logger.error(f"Error: {str(e)}")