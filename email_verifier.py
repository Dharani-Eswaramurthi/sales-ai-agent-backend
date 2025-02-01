import os
import re
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAILTESTER_API_URL = "https://happy.mailtester.ninja/ninja"
MAILTESTER_TOKEN_URL = "https://token.mailtester.ninja/token?key=yourkey"
MAILTESTER_API_KEY = os.getenv("MAILTESTER_API_KEY")

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

def get_mailtester_token(api_key: str) -> str:
    """Retrieve the authentication token from MailTester API"""
    response = requests.get(MAILTESTER_TOKEN_URL.replace("yourkey", api_key))
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    else:
        logger.error("Failed to retrieve MailTester token")
        return None

def verify_email_api(email: str, token: str) -> bool:
    """Verify email using MailTester API"""
    params = {
        "email": email,
        "token": token
    }
    response = requests.get(MAILTESTER_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        logger.info(f"API response for {email}: {data}")
        return data.get("code") == "ok"
    else:
        logger.error(f"Failed to verify {email} via API")
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
    if not MAILTESTER_API_KEY:
        logger.info("MAILTESTER_API_KEY not set")
        return None
    token = get_mailtester_token(MAILTESTER_API_KEY)
    if not token:
        return None

    for email in candidates:
        if is_valid_email_format(email):
            try:
                if verify_email_api(email, token):
                    logger.info(f"First accepted email: {email}")
                    return email
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