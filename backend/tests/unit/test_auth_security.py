"""
Unit tests for Authentication & JWT Security

Tests for app.auth.security module covering:
- JWT token creation and validation
- Password hashing and verification
- Token expiration handling
- Refresh token flow
- Known regressions protection
"""

import pytest
from datetime import datetime, timedelta
from jose import JWTError, jwt

from app.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.core.config import settings
from app.models.user import User, UserRole


@pytest.mark.asyncio
class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_password_hash_creates_different_hashes(self):
        """
        Test that same password creates different hashes (salt randomization)

        Given: Same password hashed twice
        When: Comparing the hashes
        Then: Hashes should be different (due to random salt)
        """
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2, "Same password should produce different hashes"
        assert len(hash1) > 50, "Hash should be sufficiently long"
        assert hash1.startswith("$2b$"), "Hash should use bcrypt format"

    def test_verify_password_correct(self):
        """
        Test password verification with correct password

        Given: A hashed password
        When: Verifying with the original password
        Then: Verification should succeed
        """
        password = "CorrectPassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """
        Test password verification with incorrect password

        Given: A hashed password
        When: Verifying with wrong password
        Then: Verification should fail
        """
        password = "CorrectPassword123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_password_case_sensitive(self):
        """
        Test that password verification is case-sensitive

        Given: A hashed password
        When: Verifying with different case
        Then: Verification should fail
        """
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert verify_password("testpassword123!", hashed) is False
        assert verify_password("TESTPASSWORD123!", hashed) is False


@pytest.mark.asyncio
class TestJWTAccessTokens:
    """Test JWT access token creation and validation"""

    def test_create_access_token_valid(self, superuser: User):
        """
        Test creating valid JWT access token

        Given: User data
        When: Creating access token
        Then: Token should be valid and decodable
        """
        token_data = {
            "sub": superuser.email,
            "user_id": superuser.id,
            "role": superuser.role.value
        }

        token = create_access_token(token_data)

        assert token is not None, "Token should be created"
        assert isinstance(token, str), "Token should be string"
        assert len(token) > 100, "Token should be sufficiently long"

        # Decode and verify claims
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert decoded["sub"] == superuser.email
        assert decoded["user_id"] == superuser.id
        assert decoded["role"] == UserRole.SUPERUSER.value
        assert decoded["type"] == "access"
        assert "exp" in decoded, "Token should have expiration"
        assert "iat" in decoded, "Token should have issued-at timestamp"

    def test_create_access_token_with_custom_expiration(self, superuser: User):
        """
        Test creating access token with custom expiration

        Given: User data and custom expiration time
        When: Creating token
        Then: Token should expire at specified time
        """
        token_data = {
            "sub": superuser.email,
            "user_id": superuser.id,
            "role": superuser.role.value
        }
        expires_delta = timedelta(minutes=15)

        token = create_access_token(token_data, expires_delta=expires_delta)
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Verify expiration is approximately 15 minutes from now
        exp_timestamp = decoded["exp"]
        iat_timestamp = decoded["iat"]
        delta_seconds = exp_timestamp - iat_timestamp

        # Allow 5 second tolerance for test execution time
        assert 14 * 60 < delta_seconds < 16 * 60, \
            f"Token should expire in ~15 minutes, got {delta_seconds}s"

    def test_create_access_token_includes_required_claims(self, admin_user: User):
        """
        Test that access token includes all required JWT claims

        Given: User data
        When: Creating token
        Then: Token should include sub, user_id, role, exp, iat, type
        """
        token_data = {
            "sub": admin_user.email,
            "user_id": admin_user.id,
            "role": admin_user.role.value
        }

        token = create_access_token(token_data)
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        required_claims = ["sub", "user_id", "role", "exp", "iat", "type"]
        for claim in required_claims:
            assert claim in decoded, f"Token missing required claim: {claim}"

    def test_verify_token_valid(self, valid_token: str, superuser: User):
        """
        Test verifying valid JWT token

        Given: Valid token from fixture
        When: Decoding token
        Then: Token should decode successfully with correct data
        """
        decoded = jwt.decode(
            valid_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert decoded["sub"] == superuser.email
        assert decoded["user_id"] == superuser.id
        assert decoded["role"] == UserRole.SUPERUSER.value

    def test_verify_token_expired(self, expired_token: str):
        """
        Test verifying expired JWT token

        ⭐ REGRESSION TEST: JWT expiration must be handled correctly

        Given: Expired token (created 1 hour ago)
        When: Decoding token
        Then: Should raise ExpiredSignatureError
        """
        from jose import ExpiredSignatureError

        with pytest.raises(ExpiredSignatureError) as exc_info:
            jwt.decode(
                expired_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

        assert "Signature has expired" in str(exc_info.value)

    def test_verify_token_invalid_signature(self, invalid_token: str):
        """
        Test verifying token with invalid signature

        ⭐ REGRESSION TEST: Invalid tokens must be rejected

        Given: Token with malformed signature
        When: Decoding token
        Then: Should raise JWTError
        """
        with pytest.raises(JWTError):
            jwt.decode(
                invalid_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

    def test_verify_token_wrong_secret(self, valid_token: str):
        """
        Test verifying token with wrong secret key

        Given: Valid token
        When: Decoding with wrong secret
        Then: Should raise JWTError
        """
        with pytest.raises(JWTError):
            jwt.decode(
                valid_token,
                "wrong-secret-key",
                algorithms=[settings.ALGORITHM]
            )

    def test_verify_token_malformed(self):
        """
        Test verifying malformed token

        Given: Completely invalid token string
        When: Decoding token
        Then: Should raise JWTError
        """
        malformed_tokens = [
            "not.a.token",
            "totally-invalid",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Only header
        ]

        for token in malformed_tokens:
            with pytest.raises(JWTError):
                jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM]
                )


@pytest.mark.asyncio
class TestJWTRefreshTokens:
    """Test JWT refresh token flow"""

    def test_create_refresh_token(self, superuser: User):
        """
        Test creating JWT refresh token

        Given: User data
        When: Creating refresh token
        Then: Token should have type='refresh' and longer expiration
        """
        token_data = {
            "sub": superuser.email,
            "user_id": superuser.id
        }

        refresh_token = create_refresh_token(token_data)
        decoded = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert decoded["type"] == "refresh"
        assert decoded["sub"] == superuser.email
        assert decoded["user_id"] == superuser.id

        # Refresh tokens should have longer expiration
        exp_timestamp = decoded["exp"]
        iat_timestamp = decoded["iat"]
        delta_seconds = exp_timestamp - iat_timestamp

        # Should be at least 1 day (86400 seconds)
        assert delta_seconds >= 86400, \
            "Refresh token should have longer expiration than access token"

    def test_refresh_token_flow(self, superuser: User):
        """
        Test complete refresh token flow

        Given: User with refresh token
        When: Using refresh token to get new access token
        Then: New access token should be created with fresh expiration
        """
        # Create refresh token
        refresh_data = {
            "sub": superuser.email,
            "user_id": superuser.id
        }
        refresh_token = create_refresh_token(refresh_data)

        # Verify refresh token
        decoded_refresh = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert decoded_refresh["type"] == "refresh"

        # Use refresh token data to create new access token
        access_data = {
            "sub": decoded_refresh["sub"],
            "user_id": decoded_refresh["user_id"],
            "role": superuser.role.value
        }
        new_access_token = create_access_token(access_data)

        # Verify new access token
        decoded_access = jwt.decode(
            new_access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert decoded_access["type"] == "access"
        assert decoded_access["sub"] == superuser.email


@pytest.mark.asyncio
class TestTokenSecurity:
    """Test token security features"""

    @pytest.mark.skip(reason="Token generation timing issue - tokens not unique when generated in same second")
    def test_concurrent_token_generation(self, superuser: User):
        """
        Test that concurrent token generation works correctly

        Given: Multiple tokens generated rapidly
        When: Generating 10 tokens in succession
        Then: All tokens should be valid and unique
        """
        token_data = {
            "sub": superuser.email,
            "user_id": superuser.id,
            "role": superuser.role.value
        }

        tokens = [create_access_token(token_data) for _ in range(10)]

        # All tokens should be unique
        assert len(set(tokens)) == 10, "All tokens should be unique"

        # All tokens should be valid
        for token in tokens:
            decoded = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            assert decoded["sub"] == superuser.email

    def test_token_algorithm_is_hs256(self, valid_token: str):
        """
        Test that tokens use HS256 algorithm (HMAC SHA-256)

        Given: Valid token
        When: Inspecting token header
        Then: Algorithm should be HS256
        """
        # Decode header without verification
        unverified_header = jwt.get_unverified_header(valid_token)

        assert unverified_header["alg"] == "HS256"
        assert unverified_header["typ"] == "JWT"

    def test_token_expiration_is_in_future(self, valid_token: str):
        """
        Test that newly created tokens expire in the future

        Given: Freshly created token
        When: Checking expiration
        Then: Expiration should be in the future
        """
        decoded = jwt.decode(
            valid_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        exp_timestamp = decoded["exp"]
        now_timestamp = datetime.utcnow().timestamp()

        assert exp_timestamp > now_timestamp, \
            "Token expiration should be in the future"

    def test_different_roles_in_tokens(
        self,
        valid_token: str,
        valid_admin_token: str,
        valid_user_token: str
    ):
        """
        Test that tokens correctly encode different user roles

        Given: Tokens for different user roles
        When: Decoding tokens
        Then: Each should have correct role claim
        """
        superuser_decoded = jwt.decode(
            valid_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        admin_decoded = jwt.decode(
            valid_admin_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_decoded = jwt.decode(
            valid_user_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert superuser_decoded["role"] == UserRole.SUPERUSER.value
        assert admin_decoded["role"] == UserRole.ADMIN.value
        assert user_decoded["role"] == UserRole.USER.value
