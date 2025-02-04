import os
import re
import logging
import requests
import concurrent.futures

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
        f"{first}.{last}@{domain}",      # john.doe@
        f"{first[0]}{last}@{domain}",    # jdoe@
        f"{first}{last}@{domain}",       # johndoe@
        f"{first}@{domain}",             # john@
        f"{first}{last[0]}@{domain}",    # johnd@
        # Highest probability formats (85% coverage)
        f"{first[0]}.{last}@{domain}",   # j.doe@
        f"{last}{first[0]}@{domain}",    # doej@
        f"{first}.{last[0]}@{domain}",    # john.d@
        
        # Common professional formats
        f"{first}_{last}@{domain}",      # john_doe@
        f"{last}.{first}@{domain}",      # doe.john@
        
        # Less common but valid formats
        f"{first}-{last}@{domain}",      # john-doe@
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
        if data.get("code") == "ok" or data.get("message") == "Catch-All":
            return True, data.get("message")
        else:
            logger.error(f"Failed to verify {email} via API")
            return False, data.get("message")
    else:
        logger.error(f"Failed to verify {email} via API")
        return False, data.get("message")

def verify_email_candidate(email: str, token: str) -> str | None:
    """Verify a single email candidate"""
    if is_valid_email_format(email):
        try:
            emailRef, status = verify_email_api(email, token)
            if emailRef:
                logger.info(f"First accepted email: {email}")
                return email, status
        except Exception as e:
            logger.error(f"Verification failed for {email}: {str(e)}")
    return None, status

def find_valid_email(first_name: str, last_name: str, domain: str) -> str | None:
    """Find valid email based on first successful verification"""
    if not all([first_name, last_name, domain]):
        logger.error("Missing required input parameters")
        return None, None

    if not is_valid_email_format(f"test@{domain}"):
        logger.error(f"Invalid domain format: {domain}")
        return None, None

    candidates = generate_email_combinations(first_name, last_name, domain)
    if not MAILTESTER_API_KEY:
        logger.info("MAILTESTER_API_KEY not set")
        return None, None
    token = get_mailtester_token(MAILTESTER_API_KEY)
    if not token:
        return None, None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_email = {executor.submit(verify_email_candidate, email, token): email for email in candidates}
        for future in concurrent.futures.as_completed(future_to_email):
            email = future_to_email[future]
            try:
                result, status = future.result()
                if result:
                    return result, status
            except Exception as e:
                logger.error(f"Verification failed for {email}: {str(e)}")

    logger.info("No deliverable email found")
    return None, None

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