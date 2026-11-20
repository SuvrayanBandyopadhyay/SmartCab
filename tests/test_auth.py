
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_employee_login():
    response = client.post(
        "/auth/login",
        json={
            "email": "employee@X.test",
            "password": "employee123",
            "company_id": 1
        }
    )

    print("Status:", response.status_code)
    print("Response:", response.json())

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


if __name__ == "__main__":
    test_employee_login()
