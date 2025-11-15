"""
Unit tests for Password Policy Validator
"""

import pytest
from app.auth.password_policy import PasswordPolicy, validate_password


class TestPasswordPolicy:
    """Test password policy validation"""

    def test_valid_strong_password(self):
        """Test that a strong password passes validation"""
        password = "MyStr0ng!Pass@2024"
        is_valid, errors, score = validate_password(password)

        assert is_valid is True
        assert len(errors) == 0
        assert score >= 60

    def test_password_too_short(self):
        """Test that password shorter than minimum length fails"""
        password = "Short1!"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("at least" in error for error in errors)

    def test_password_missing_uppercase(self):
        """Test that password without uppercase fails"""
        password = "mypassword123!"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("uppercase" in error for error in errors)

    def test_password_missing_lowercase(self):
        """Test that password without lowercase fails"""
        password = "MYPASSWORD123!"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("lowercase" in error for error in errors)

    def test_password_missing_digit(self):
        """Test that password without digit fails"""
        password = "MyPassword!"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("digit" in error for error in errors)

    def test_password_missing_symbol(self):
        """Test that password without symbol fails"""
        password = "MyPassword123"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("symbol" in error for error in errors)

    def test_common_password(self):
        """Test that common passwords are rejected"""
        password = "Password123!"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("common" in error.lower() for error in errors)

    def test_password_similar_to_username(self):
        """Test that password similar to username fails"""
        password = "JohnDoe123!"
        username = "johndoe"
        is_valid, errors, score = validate_password(password, username=username)

        assert is_valid is False
        assert any("similar to username" in error for error in errors)

    def test_password_similar_to_email(self):
        """Test that password similar to email fails"""
        password = "TestUser123!"
        email = "testuser@example.com"
        is_valid, errors, score = validate_password(password, email=email)

        assert is_valid is False
        assert any("similar to email" in error for error in errors)

    def test_password_strength_calculation(self):
        """Test password strength scoring"""
        weak_password = "Pass123!"
        medium_password = "MyGoodPass123!"
        strong_password = "MyV3ry$tr0ng!P@ssw0rd2024"

        _, _, weak_score = validate_password(weak_password)
        _, _, medium_score = validate_password(medium_password)
        _, _, strong_score = validate_password(strong_password)

        assert weak_score < medium_score < strong_password

    def test_password_entropy_calculation(self):
        """Test entropy calculation"""
        password = "MyStr0ng!P@ss"
        entropy = PasswordPolicy.calculate_entropy(password)

        # Should have reasonable entropy with mixed character types
        assert entropy > 50

    def test_generate_strong_password(self):
        """Test strong password generation"""
        password = PasswordPolicy.generate_strong_password(length=16)

        is_valid, errors, score = validate_password(password)

        assert len(password) == 16
        assert is_valid is True
        assert score >= 70

    def test_sequential_characters_detection(self):
        """Test detection of sequential characters"""
        password = "MyPass123456!"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("sequential" in error.lower() for error in errors)

    def test_repeated_characters_detection(self):
        """Test detection of repeated characters"""
        password = "MyPasssss123!"
        is_valid, errors, score = validate_password(password)

        assert is_valid is False
        assert any("repeated" in error.lower() for error in errors)

    def test_password_strength_labels(self):
        """Test strength label generation"""
        assert PasswordPolicy.get_strength_label(10) == "Very Weak"
        assert PasswordPolicy.get_strength_label(30) == "Weak"
        assert PasswordPolicy.get_strength_label(50) == "Moderate"
        assert PasswordPolicy.get_strength_label(70) == "Strong"
        assert PasswordPolicy.get_strength_label(90) == "Very Strong"
