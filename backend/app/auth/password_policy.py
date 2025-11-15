"""
Orizon Zero Trust Connect - Password Policy Validator
For: Marco @ Syneto/Orizon

Comprehensive password policy enforcement with:
- Minimum length requirements
- Complexity requirements (uppercase, lowercase, numbers, symbols)
- Common password blacklist
- Username/email similarity check
- Password history tracking
- Entropy calculation
"""

import re
import math
from typing import Tuple, List, Optional
from datetime import datetime
from loguru import logger

from app.core.config import settings


class PasswordPolicy:
    """
    Password Policy Validator

    Features:
    - Configurable minimum length (default: 12)
    - Complexity requirements (uppercase, lowercase, digit, symbol)
    - Common password blacklist (rockyou.txt top 10k)
    - Username/email similarity detection
    - Password strength scoring (0-100)
    - Entropy calculation
    - Password history checking
    """

    # Policy configuration
    MIN_LENGTH = getattr(settings, "PASSWORD_MIN_LENGTH", 12)
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SYMBOL = True

    # Blacklist settings
    BLACKLIST_ENABLED = True
    BLACKLIST_SIZE = 10000  # Top 10k most common passwords

    # Similarity settings
    MAX_USERNAME_SIMILARITY = 0.7  # 70% similar is too much
    MAX_EMAIL_SIMILARITY = 0.7

    # Common weak passwords (subset - in production load from file)
    COMMON_PASSWORDS = {
        "password", "123456", "12345678", "qwerty", "abc123", "monkey",
        "1234567", "letmein", "trustno1", "dragon", "baseball", "iloveyou",
        "master", "sunshine", "ashley", "bailey", "passw0rd", "shadow",
        "123123", "654321", "superman", "qazwsx", "michael", "football",
        "password1", "password123", "admin", "root", "administrator",
        "orizon", "syneto", "zerotrust", "connect"
    }

    # Character sets for entropy calculation
    CHAR_SETS = {
        'lowercase': 'abcdefghijklmnopqrstuvwxyz',
        'uppercase': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'digits': '0123456789',
        'symbols': '!@#$%^&*()_+-=[]{}|;:,.<>?'
    }

    @classmethod
    def validate_password(
        cls,
        password: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        old_passwords: Optional[List[str]] = None
    ) -> Tuple[bool, List[str], int]:
        """
        Validate password against policy

        Args:
            password: Password to validate
            username: Username (optional, for similarity check)
            email: Email (optional, for similarity check)
            old_passwords: List of previous password hashes (for history check)

        Returns:
            Tuple of:
            - is_valid (bool): True if password passes all checks
            - errors (List[str]): List of validation error messages
            - strength_score (int): Password strength score (0-100)
        """
        errors = []

        # Check 1: Minimum length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")

        # Check 2: Maximum length (prevent DoS)
        if len(password) > 128:
            errors.append("Password must not exceed 128 characters")

        # Check 3: Complexity requirements
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        if cls.REQUIRE_DIGIT and not re.search(r'[0-9]', password):
            errors.append("Password must contain at least one digit")

        if cls.REQUIRE_SYMBOL and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            errors.append("Password must contain at least one symbol (!@#$%^&* etc.)")

        # Check 4: Common password blacklist
        if cls.BLACKLIST_ENABLED:
            if password.lower() in cls.COMMON_PASSWORDS:
                errors.append("Password is too common and easily guessable")

            # Check for common patterns
            if cls._contains_common_pattern(password):
                errors.append("Password contains common patterns (e.g., 'password', '123456')")

        # Check 5: Sequential characters
        if cls._has_sequential_chars(password):
            errors.append("Password contains too many sequential characters")

        # Check 6: Repeated characters
        if cls._has_repeated_chars(password):
            errors.append("Password contains too many repeated characters")

        # Check 7: Username similarity
        if username and cls._is_too_similar(password, username):
            errors.append("Password is too similar to username")

        # Check 8: Email similarity
        if email:
            email_username = email.split('@')[0]
            if cls._is_too_similar(password, email_username):
                errors.append("Password is too similar to email address")

        # Check 9: Password history (if provided)
        if old_passwords:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

            for old_hash in old_passwords:
                if pwd_context.verify(password, old_hash):
                    errors.append("Password has been used recently. Please choose a different password")
                    break

        # Calculate strength score
        strength_score = cls.calculate_strength(password)

        # Overall validation
        is_valid = len(errors) == 0

        if is_valid:
            logger.debug(f"✅ Password validation passed (strength: {strength_score}/100)")
        else:
            logger.debug(f"❌ Password validation failed: {', '.join(errors)}")

        return is_valid, errors, strength_score

    @classmethod
    def calculate_strength(cls, password: str) -> int:
        """
        Calculate password strength score (0-100)

        Factors:
        - Length (up to 30 points)
        - Character diversity (up to 30 points)
        - Entropy (up to 40 points)

        Args:
            password: Password to evaluate

        Returns:
            Strength score (0-100)
        """
        score = 0

        # Factor 1: Length (max 30 points)
        length_score = min(30, (len(password) / cls.MIN_LENGTH) * 15)
        score += length_score

        # Factor 2: Character diversity (max 30 points)
        diversity_score = 0

        if re.search(r'[a-z]', password):
            diversity_score += 5

        if re.search(r'[A-Z]', password):
            diversity_score += 5

        if re.search(r'[0-9]', password):
            diversity_score += 5

        if re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            diversity_score += 10

        # Bonus for mixing character types
        char_types = sum([
            bool(re.search(r'[a-z]', password)),
            bool(re.search(r'[A-Z]', password)),
            bool(re.search(r'[0-9]', password)),
            bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password))
        ])

        if char_types >= 4:
            diversity_score += 5

        score += diversity_score

        # Factor 3: Entropy (max 40 points)
        entropy = cls.calculate_entropy(password)
        entropy_score = min(40, (entropy / 80) * 40)  # 80 bits is considered strong
        score += entropy_score

        # Penalties
        # Penalty for common passwords
        if password.lower() in cls.COMMON_PASSWORDS:
            score = max(0, score - 30)

        # Penalty for sequential chars
        if cls._has_sequential_chars(password):
            score = max(0, score - 20)

        # Penalty for repeated chars
        if cls._has_repeated_chars(password):
            score = max(0, score - 15)

        return int(min(100, score))

    @classmethod
    def calculate_entropy(cls, password: str) -> float:
        """
        Calculate password entropy in bits

        Entropy = log2(charset_size ^ password_length)

        Args:
            password: Password to calculate entropy for

        Returns:
            Entropy in bits
        """
        # Determine character set size
        charset_size = 0

        if re.search(r'[a-z]', password):
            charset_size += len(cls.CHAR_SETS['lowercase'])

        if re.search(r'[A-Z]', password):
            charset_size += len(cls.CHAR_SETS['uppercase'])

        if re.search(r'[0-9]', password):
            charset_size += len(cls.CHAR_SETS['digits'])

        if re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            charset_size += len(cls.CHAR_SETS['symbols'])

        if charset_size == 0:
            return 0.0

        # Calculate entropy
        entropy = len(password) * math.log2(charset_size)

        return entropy

    @classmethod
    def get_strength_label(cls, score: int) -> str:
        """
        Get human-readable strength label

        Args:
            score: Strength score (0-100)

        Returns:
            Strength label
        """
        if score >= 80:
            return "Very Strong"
        elif score >= 60:
            return "Strong"
        elif score >= 40:
            return "Moderate"
        elif score >= 20:
            return "Weak"
        else:
            return "Very Weak"

    @classmethod
    def _contains_common_pattern(cls, password: str) -> bool:
        """Check if password contains common patterns"""
        common_patterns = [
            r'password',
            r'pass\d+',
            r'123+',
            r'qwerty',
            r'abc+',
            r'admin',
            r'root',
            r'user',
            r'test'
        ]

        password_lower = password.lower()

        for pattern in common_patterns:
            if re.search(pattern, password_lower):
                return True

        return False

    @classmethod
    def _has_sequential_chars(cls, password: str, threshold: int = 3) -> bool:
        """
        Check if password has too many sequential characters

        Args:
            password: Password to check
            threshold: Max sequential chars allowed

        Returns:
            True if too many sequential chars found
        """
        # Check for sequential numbers (123, 234, etc.)
        for i in range(len(password) - threshold + 1):
            substr = password[i:i+threshold]

            # Check if numeric and sequential
            if substr.isdigit():
                chars = [int(c) for c in substr]
                if all(chars[j] + 1 == chars[j + 1] for j in range(len(chars) - 1)):
                    return True

            # Check if alphabetic and sequential
            if substr.isalpha():
                chars = [ord(c.lower()) for c in substr]
                if all(chars[j] + 1 == chars[j + 1] for j in range(len(chars) - 1)):
                    return True

        return False

    @classmethod
    def _has_repeated_chars(cls, password: str, threshold: int = 3) -> bool:
        """
        Check if password has too many repeated characters

        Args:
            password: Password to check
            threshold: Max repeated chars allowed

        Returns:
            True if too many repeated chars found
        """
        for i in range(len(password) - threshold + 1):
            substr = password[i:i+threshold]

            # Check if all characters are the same
            if len(set(substr)) == 1:
                return True

        return False

    @classmethod
    def _is_too_similar(cls, password: str, reference: str) -> bool:
        """
        Check if password is too similar to reference string

        Uses Levenshtein distance ratio

        Args:
            password: Password to check
            reference: Reference string (username, email, etc.)

        Returns:
            True if too similar
        """
        from difflib import SequenceMatcher

        # Normalize strings
        password_lower = password.lower()
        reference_lower = reference.lower()

        # Calculate similarity ratio
        ratio = SequenceMatcher(None, password_lower, reference_lower).ratio()

        return ratio >= cls.MAX_USERNAME_SIMILARITY

    @classmethod
    def generate_strong_password(cls, length: int = 16) -> str:
        """
        Generate a cryptographically strong random password

        Args:
            length: Password length (default: 16)

        Returns:
            Generated password
        """
        import secrets
        import string

        # Ensure we have characters from all required sets
        password = []

        if cls.REQUIRE_UPPERCASE:
            password.append(secrets.choice(string.ascii_uppercase))

        if cls.REQUIRE_LOWERCASE:
            password.append(secrets.choice(string.ascii_lowercase))

        if cls.REQUIRE_DIGIT:
            password.append(secrets.choice(string.digits))

        if cls.REQUIRE_SYMBOL:
            password.append(secrets.choice('!@#$%^&*()_+-=[]{}|;:,.<>?'))

        # Fill remaining length with random characters from all sets
        all_chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'

        for _ in range(length - len(password)):
            password.append(secrets.choice(all_chars))

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)


# Convenience function
def validate_password(
    password: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    old_passwords: Optional[List[str]] = None
) -> Tuple[bool, List[str], int]:
    """
    Validate password against policy

    Args:
        password: Password to validate
        username: Username (optional)
        email: Email (optional)
        old_passwords: Previous password hashes (optional)

    Returns:
        Tuple of (is_valid, errors, strength_score)
    """
    return PasswordPolicy.validate_password(password, username, email, old_passwords)
