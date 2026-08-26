import asyncio
import httpx
import uuid
import bcrypt
import hashlib
from app.main import app
from app.core.security import hash_password, verify_password

async def test_security_directly():
    print("=== Testing security.py Hashing Directly ===")
    
    # 1. Test normal hashing and verification
    pw = "mySecretPassword123!"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed) is True
    assert verify_password(pw + "wrong", hashed) is False
    
    # 2. Test password longer than 72 bytes
    long_pw = "a" * 100
    hashed_long = hash_password(long_pw)
    assert verify_password(long_pw, hashed_long) is True
    assert verify_password(long_pw + "b", hashed_long) is False
    
    # 3. Test legacy password verification (raw bcrypt hash without SHA-256 pre-hashing)
    # Generate legacy hash directly using bcrypt
    legacy_pw = "legacy123!"
    legacy_hash = bcrypt.hashpw(legacy_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    assert verify_password(legacy_pw, legacy_hash) is True
    assert verify_password(legacy_pw + "wrong", legacy_hash) is False
    
    # 4. Test legacy password > 72 bytes doesn't fail with 500, verified safely as False or True depending on compatibility
    # Since standard bcrypt cannot verify raw > 72 bytes without raising ValueError or truncating,
    # verify_password catches ValueError and returns False, avoiding 500.
    legacy_long_pw = "a" * 100
    # Create invalid hash to test exception safety
    invalid_hash = "invalid_hash_value"
    assert verify_password(legacy_long_pw, invalid_hash) is False
    
    print("Direct security.py tests passed!")

async def test_api_endpoints():
    print("=== Testing HTTP API Endpoints ===")
    suffix = uuid.uuid4().hex[:12]
    email = f"auth-test-{suffix}@example.com"
    pw = "MyPass123!"
    long_pw = "a" * 100
    
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. nonexistent email + password -> 401
        print("A. Testing nonexistent email + password...")
        res = await client.post("/auth/login", json={"email": "nonexistent@example.com", "password": "any"})
        assert res.status_code == 401
        assert "detail" in res.json()
        
        # B. Register user with standard password
        print("Registering user...")
        res = await client.post("/auth/register", json={
            "name": "Auth Test User",
            "email": email,
            "password": pw,
            "business_name": f"Auth Business {suffix}"
        })
        assert res.status_code == 201
        
        # C. existing email + wrong password -> 401
        print("C. Testing existing email + wrong password...")
        res = await client.post("/auth/login", json={"email": email, "password": pw + "wrong"})
        assert res.status_code == 401
        assert "detail" in res.json()
        
        # D. existing email + correct password -> 200 + JWT
        print("D. Testing existing email + correct password...")
        res = await client.post("/auth/login", json={"email": email, "password": pw})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        
        # E. Register and log in user with password longer than 72 bytes
        print("E. Testing password longer than 72 bytes...")
        suffix_long = uuid.uuid4().hex[:12]
        email_long = f"auth-test-long-{suffix_long}@example.com"
        
        res = await client.post("/auth/register", json={
            "name": "Auth Test Long User",
            "email": email_long,
            "password": long_pw,
            "business_name": f"Auth Business Long {suffix_long}"
        })
        assert res.status_code == 201
        
        # Log in with long password
        res = await client.post("/auth/login", json={"email": email_long, "password": long_pw})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        
        # Log in with long password + wrong suffix
        res = await client.post("/auth/login", json={"email": email_long, "password": long_pw + "extra"})
        assert res.status_code == 401
        assert "detail" in res.json()

        # F. CORS verification
        print("F. Testing CORS on recoup-one.vercel.app...")
        cors_headers = {
            "Origin": "https://recoup-one.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
        res = await client.options("/auth/login", headers=cors_headers)
        assert res.status_code in [200, 204]
        assert res.headers.get("access-control-allow-origin") == "https://recoup-one.vercel.app"
        assert res.headers.get("access-control-allow-credentials") == "true"
        
        # Also test direct POST request with Origin header
        res = await client.post("/auth/login", json={"email": email, "password": pw}, headers={"Origin": "https://recoup-one.vercel.app"})
        assert res.headers.get("access-control-allow-origin") == "https://recoup-one.vercel.app"
        assert res.headers.get("access-control-allow-credentials") == "true"

    print("HTTP API Endpoint tests passed!")

async def main():
    await test_security_directly()
    await test_api_endpoints()
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
