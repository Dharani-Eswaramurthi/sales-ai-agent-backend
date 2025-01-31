import re
import dns.resolver
import socket
import smtplib
from typing import Dict, List, Tuple
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

class AdvancedEmailValidator:
    """
    Custom email validation system with:
    - Multi-layer verification
    - Dynamic pattern scoring
    - Domain-specific pattern detection
    - Risk analysis
    """
    
    def __init__(self):
        self.common_patterns = [
            ('{first}.{last}', 'first_last', 0.9),
            ('{first}_{last}', 'underscore', 0.85),
            ('{f}{last}', 'initial_last', 0.8),
            ('{first}{l}', 'first_initial', 0.75),
            ('{last}.{first}', 'last_first', 0.7),
            ('{f}{l}', 'initials', 0.6)
        ]
        self.disposable_domains = self._load_disposable_domains()
        self.role_accounts = ['admin', 'support', 'info', 'contact', 'sales']
        self.user_agent = 'Mozilla/5.0 (compatible; EmailValidator/1.0; +https://example.com/bot)'

    def validate_email(self, email: str) -> Dict:
        """Main validation method with detailed results"""
        result = {
            'email': email,
            'valid': False,
            'score': 0.0,
            'checks': {
                'syntax': False,
                'mx_records': False,
                'disposable': False,
                'role_account': False,
                'smtp_verify': False,
                'web_presence': False
            },
            'details': {}
        }

        if not self._check_syntax(email):
            return result

        result['checks']['syntax'] = True
        domain = email.split('@')[1]
        local_part = email.split('@')[0]

        # Basic checks
        result['checks']['mx_records'] = self._check_mx_records(domain)
        result['checks']['disposable'] = self._is_disposable_domain(domain)
        result['checks']['role_account'] = self._is_role_account(local_part)

        # Advanced checks
        result['checks']['smtp_verify'] = self._smtp_verify(email)
        result['checks']['web_presence'] = self._check_web_presence(domain, local_part)

        # Calculate score
        result['score'] = self._calculate_score(result['checks'])
        result['valid'] = result['score'] >= 0.7  # Adjust threshold as needed

        return result

    def generate_emails(self, first: str, last: str, domain: str) -> List[Tuple[str, float]]:
        """Generate scored email patterns for a domain"""
        domain_patterns = self._analyze_domain_patterns(domain)
        suggestions = []

        for pattern, pattern_type, base_score in self.common_patterns:
            email = pattern.format(
                first=first.lower(),
                last=last.lower(),
                f=first[0].lower(),
                l=last[0].lower()
            ) + f'@{domain}'
            
            # Apply domain-specific pattern boost
            score = base_score * domain_patterns.get(pattern_type, 1.0)
            suggestions.append((email, min(score, 1.0)))

        return sorted(suggestions, key=lambda x: x[1], reverse=True)

    def _analyze_domain_patterns(self, domain: str) -> Dict[str, float]:
        """Determine domain-specific pattern weights"""
        patterns = {}
        
        # Check website for contact patterns
        web_patterns = self._scan_website_patterns(domain)
        if web_patterns:
            patterns.update(web_patterns)
        
        # Check MX provider patterns
        mx_patterns = self._detect_mx_provider_patterns(domain)
        patterns.update(mx_patterns)

        return patterns

    def _scan_website_patterns(self, domain: str) -> Dict[str, float]:
        """Attempt to find email patterns on company website"""
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(f'http://{domain}', headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            emails = set()
            for link in soup.find_all('a', href=True):
                if 'mailto:' in link['href']:
                    email = link['href'].split(':')[1].split('?')[0]
                    emails.add(email)
            
            pattern_counts = defaultdict(int)
            for email in emails:
                local_part = email.split('@')[0]
                if '.' in local_part:
                    pattern_counts['first_last'] += 1
                elif '_' in local_part:
                    pattern_counts['underscore'] += 1
                elif len(local_part) == 2:
                    pattern_counts['initials'] += 1
            
            total = sum(pattern_counts.values()) or 1
            return {k: v/total for k, v in pattern_counts.items()}
        except:
            return {}

    def _detect_mx_provider_patterns(self, domain: str) -> Dict[str, float]:
        """Guess patterns based on MX record provider"""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_host = str(mx_records[0].exchange).lower()
            
            if 'google' in mx_host:
                return {'first_last': 1.2, 'initial_last': 1.1}
            if 'outlook' in mx_host or 'office365' in mx_host:
                return {'first_last': 1.1, 'initials': 0.9}
            if 'amazonaws' in mx_host:
                return {'underscore': 1.3, 'first_last': 0.8}
            return {}
        except:
            return {}

    def _calculate_score(self, checks: Dict) -> float:
        """Calculate composite validation score"""
        weights = {
            'syntax': 0.15,
            'mx_records': 0.25,
            'disposable': -0.5,
            'role_account': -0.2,
            'smtp_verify': 0.3,
            'web_presence': 0.1
        }
        
        score = 0
        for check, value in checks.items():
            if value:
                score += weights.get(check, 0)
        return max(0, min(1, score))

    # Helper methods for individual checks
    def _check_syntax(self, email: str) -> bool:
        regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.fullmatch(regex, email) is not None

    def _check_mx_records(self, domain: str) -> bool:
        try:
            return len(dns.resolver.resolve(domain, 'MX')) > 0
        except:
            return False

    def _is_disposable_domain(self, domain: str) -> bool:
        return domain.lower() in self.disposable_domains

    def _is_role_account(self, local_part: str) -> bool:
        return any(role in local_part.lower() for role in self.role_accounts)

    def _smtp_verify(self, email: str) -> bool:
        domain = email.split('@')[1]
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_host = str(mx_records[0].exchange)
            with smtplib.SMTP(mx_host, timeout=10) as server:
                server.helo()
                server.mail('')
                code, _ = server.rcpt(email)
                return code == 250
        except:
            return False

    def _check_web_presence(self, domain: str, local_part: str) -> bool:
        try:
            response = requests.get(
                f'https://{domain}/.well-known/security.txt',
                timeout=3
            )
            if response.status_code == 200:
                return local_part in response.text
        except:
            return False

    def _load_disposable_domains(self) -> set:
        # Load from updated disposable domains list
        return {
            'mailinator.com', 'tempmail.com', '10minutemail.com',
            'guerrillamail.com', 'throwawaymail.com', 'fakeinbox.com'
        }

# Usage Example
if __name__ == "__main__":
    validator = AdvancedEmailValidator()
    
    # Generate email suggestions
    domain = "clarishealth.com"
    first_name = "jeffrey"
    last_name = "Mcneese"
    
    print(f"Generating email suggestions for {first_name} {last_name} @{domain}:")
    suggestions = validator.generate_emails(first_name, last_name, domain)
    
    for email, score in suggestions[:5]:
        validation = validator.validate_email(email)
        print(f"\nEmail: {email}")
        print(f"Generated Score: {score:.2f}")
        print(f"Validation Score: {validation['score']:.2f}")
        print(f"Valid: {validation['valid']}")
        print("Details:")
        for check, value in validation['checks'].items():
            print(f"- {check}: {value}")