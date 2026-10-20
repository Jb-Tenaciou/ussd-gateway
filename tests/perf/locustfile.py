"""Test de charge. Lancer l'API, puis :
    pip install locust
    LOAD_PHONE=+25779222222 LOAD_PASSWORD=... locust -f tests/perf/locustfile.py \
        --host http://localhost:8000 --users 20 --spawn-rate 5 --run-time 1m --headless
"""
import os
import uuid

from locust import HttpUser, between, task


class UssdUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        r = self.client.post("/api/v1/auth/login", json={
            "phone_number": os.environ["LOAD_PHONE"], "password": os.environ["LOAD_PASSWORD"]})
        self.h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    @task
    def parcours(self):
        s = self.client.post("/api/v1/sessions", headers=self.h, json={"phone_number": "+25779000999"}).json()
        self.client.post(f"/api/v1/sessions/{s['id']}/interactions", headers=self.h,
                         json={"menu_code": "MAIN", "user_input": "1"})
        tx = self.client.post("/api/v1/transactions", headers=self.h,
                              json={"amount": "1000", "idempotency_key": uuid.uuid4().hex}).json()
        self.client.patch(f"/api/v1/transactions/{tx['id']}/status", headers=self.h, json={"status": "SUCCESS"})
        self.client.get("/health")
