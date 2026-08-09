import asyncio
from httpx import AsyncClient, ASGITransport
import sys

from app.main import app

async def main():
    print("=== SCHOLAROS E2E QA AUDIT & VERIFICATION (ASGI IN-MEMORY) ===")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register Student A & B
        resp_a = await client.post("/api/v1/auth/register", json={
            "email": "qastudent_a@gmail.com",
            "password": "Password123!",
            "full_name": "QA Student A"
        })
        print(f"Register Student A Status: {resp_a.status_code}")

        resp_b = await client.post("/api/v1/auth/register", json={
            "email": "qastudent_b@gmail.com",
            "password": "Password123!",
            "full_name": "QA Student B"
        })
        print(f"Register Student B Status: {resp_b.status_code}")

        # 2. Login Student A
        login_a = await client.post("/api/v1/auth/login", json={
            "email": "qastudent_a@gmail.com",
            "password": "Password123!"
        })
        token_a = login_a.json().get("access_token")
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 3. RBAC Isolation Test: Student A accessing Admin endpoint
        forbidden_resp = await client.get("/api/v1/admin/users", headers=headers_a)
        print(f"Student A Admin Endpoint Access Status (Expected 403): {forbidden_resp.status_code}")
        assert forbidden_resp.status_code == 403, "SECURITY FAIL: Student bypassed admin check!"
        print("PASS: RBAC Isolation - Non-admin users are rejected with HTTP 403 Forbidden.")

        # 4. Login Admin
        login_admin = await client.post("/api/v1/auth/login", json={
            "email": "admin2009@gmail.com",
            "password": "admin200968"
        })
        token_admin = login_admin.json().get("access_token")
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # 5. Admin User Management & Privacy Inspection
        admin_users_resp = await client.get("/api/v1/admin/users", headers=headers_admin)
        print(f"Admin /users Status: {admin_users_resp.status_code}")
        users_list = admin_users_resp.json()
        assert any("raw_password" in u for u in users_list) == False, "SECURITY VULNERABILITY: raw_password present in API response!"
        print("PASS: Data Privacy - raw_password is completely purged from API responses.")

        # 6. Admin Inspect User (Triggers Audit Log)
        inspect_resp = await client.get(f"/api/v1/admin/users/{users_list[0]['id']}/inspect", headers=headers_admin)
        print(f"Admin Inspect User Status: {inspect_resp.status_code}")

        # 7. Admin Fetch Platform Audit Logs
        audit_resp = await client.get("/api/v1/admin/audit-logs", headers=headers_admin)
        print(f"Admin Audit Logs Status: {audit_resp.status_code}, Recorded Logs: {len(audit_resp.json())}")
        assert len(audit_resp.json()) > 0, "FAIL: Audit logs were not recorded!"
        print("PASS: Audit Trail - Operations are persistently logged in database.")

        # 8. Friend Request Lifecycle
        friend_req = await client.post("/api/v1/connect/friends/request?target_username_or_id=QA Student B", headers=headers_a)
        print(f"Friend Request Status: {friend_req.status_code}")
        conn_id = friend_req.json().get("id")

        # Login Student B to accept
        login_b = await client.post("/api/v1/auth/login", json={
            "email": "qastudent_b@gmail.com",
            "password": "Password123!"
        })
        headers_b = {"Authorization": f"Bearer {login_b.json().get('access_token')}"}

        accept_resp = await client.patch(f"/api/v1/connect/friends/{conn_id}/accept", headers=headers_b)
        print(f"Student B Accept Request Status: {accept_resp.status_code}")
        assert accept_resp.status_code == 200, "FAIL to accept friend request"
        print("PASS: Friend Lifecycle - Friend request sent and accepted successfully.")

        # 9. Resource Sharing Isolation
        share_resp = await client.post("/api/v1/connect/resources/share", json={
            "shared_with_id": friend_req.json().get("addressee_id"),
            "resource_type": "note",
            "resource_id": "test-note-id-123",
            "permission": "view_only"
        }, headers=headers_a)
        print(f"Resource Share Status: {share_resp.status_code}")
        assert share_resp.status_code == 201, "FAIL to share resource"
        print("PASS: Resource Sharing - Resource-level permission created successfully.")

    print("\n=== ALL E2E QA AUDIT TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(main())
