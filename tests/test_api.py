def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_login_fail_and_protected(client):
    r = client.post("/api/v1/auth/login", json={"phone_number": "+25779000000", "password": "mauvais"})
    assert r.status_code == 401
    assert client.get("/api/v1/users").status_code == 401


def test_roles(client, admin, demo):
    assert client.get("/api/v1/users", headers=demo).status_code == 403
    assert client.get("/api/v1/users", headers=admin).status_code == 200
    r = client.post("/api/v1/users", headers=admin,
                    json={"full_name": "Op", "phone_number": "+25779222222", "password": "Operator123", "role": "OPERATOR"})
    assert r.status_code == 201 and "password" not in r.text


def test_validation(client, admin):
    r = client.post("/api/v1/sessions", headers=admin, json={"phone_number": "abc"})
    assert r.status_code == 422
    r = client.post("/api/v1/transactions", headers=admin, json={"amount": -5, "idempotency_key": "12345678"})
    assert r.status_code == 422


def test_session_flow(client, admin):
    s = client.post("/api/v1/sessions", headers=admin, json={"phone_number": "+25779111111"}).json()
    i = client.post(f"/api/v1/sessions/{s['id']}/interactions", headers=admin,
                    json={"menu_code": "MAIN", "user_input": "1", "system_response": "Montant ?"}).json()
    assert i["step_number"] == 1
    r = client.patch(f"/api/v1/sessions/{s['id']}", headers=admin, json={"session_state": "CANCELLED"})
    assert r.json()["session_state"] == "CANCELLED"
    r = client.post(f"/api/v1/sessions/{s['id']}/interactions", headers=admin, json={"menu_code": "MAIN"})
    assert r.status_code == 409


def test_transaction_idempotency_and_transitions(client, admin):
    body = {"amount": "5000", "idempotency_key": "KEY-0001-ABC"}
    a = client.post("/api/v1/transactions", headers=admin, json=body).json()
    b = client.post("/api/v1/transactions", headers=admin, json=body).json()
    assert a["id"] == b["id"] and a["reference"].startswith("DEMO-")
    assert len(client.get("/api/v1/transactions", headers=admin).json()) == 1
    ok = client.patch(f"/api/v1/transactions/{a['id']}/status", headers=admin, json={"status": "SUCCESS"})
    assert ok.json()["status"] == "SUCCESS" and ok.json()["completed_at"]
    bad = client.patch(f"/api/v1/transactions/{a['id']}/status", headers=admin, json={"status": "FAILED"})
    assert bad.status_code == 409


def test_sms_and_audit(client, admin, demo):
    s = client.post("/api/v1/sms", headers=admin,
                    json={"phone_number": "+25779111111", "message_text": "Paiement réussi DEMO-001"}).json()
    assert s["status"] == "QUEUED"
    s2 = client.patch(f"/api/v1/sms/{s['id']}/status", headers=admin, json={"status": "SENT"}).json()
    assert s2["sent_at"]
    assert client.get("/api/v1/audit-logs", headers=admin).status_code == 200
    assert client.get("/api/v1/audit-logs", headers=demo).status_code == 403
