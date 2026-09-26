import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

client = TestClient(app)


def test_health_check():
    """Test backend is running"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    print("✅ Health check passed")


def test_create_business_missing_name():
    """Test validation - business name required"""
    with open("test_sample.txt", "w") as f:
        f.write("Test content")

    with open("test_sample.txt", "rb") as f:
        response = client.post(
            "/api/business",
            data={"language": "gu"},
            files={"file": ("test_sample.txt", f)},
        )

    os.remove("test_sample.txt")
    assert response.status_code == 400
    print("✅ Validation test (missing name) passed")


def test_create_business_invalid_language():
    """Test validation - invalid language"""
    with open("test_sample.txt", "w") as f:
        f.write("Test content")

    with open("test_sample.txt", "rb") as f:
        response = client.post(
            "/api/business",
            data={"name": "Test Store", "language": "fr"},
            files={"file": ("test_sample.txt", f)},
        )

    os.remove("test_sample.txt")
    assert response.status_code == 400
    print("✅ Validation test (invalid language) passed")


def test_create_business_success():
    """Test successful business registration"""
    with open("test_sample.txt", "w") as f:
        f.write("Toor dal - Rs 45/kg\nChana dal - Rs 50/kg\nStore hours: 9AM-9PM")

    with open("test_sample.txt", "rb") as f:
        response = client.post(
            "/api/business",
            data={"name": "Test Store", "language": "gu"},
            files={"file": ("test_sample.txt", f)},
        )

    os.remove("test_sample.txt")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "business_id" in data
    assert data["voice_webhook_url"].endswith(f"/voice/answer/{data['business_id']}")
    print("✅ Business registration test passed")


def test_get_nonexistent_business():
    """Test 404 for missing business"""
    response = client.get("/api/business/nonexistent")
    assert response.status_code == 404
    print("✅ Not found test passed")


def test_list_businesses():
    """Test getting all businesses"""
    response = client.get("/api/businesses")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "businesses" in data
    print("✅ List businesses test passed")


def test_analytics():
    """Test analytics endpoint"""
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_businesses" in data
    print("✅ Analytics test passed")


def test_voice_answer_unknown_business_returns_empty_ncco():
    """Voice webhook for unknown business must return empty NCCO, not crash"""
    response = client.post("/voice/answer/does-not-exist")
    assert response.status_code == 200
    assert response.json() == []
    print("✅ Voice webhook (unknown business) test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
