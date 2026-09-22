"""Critical business-rule tests for the Laptop Allocation Management System."""

from tests.conftest import get_admin_token


def _all_available_numbers(client, headers):
    resp = client.get("/api/v1/allocations/available-laptops", headers=headers)
    assert resp.status_code == 200
    return [l["laptop_number"] for l in resp.json()]


def test_auth_required_for_dashboard_stats(client):
    resp = client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 401


def test_invalid_login_rejected(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_invalid_token_rejected(client):
    resp = client.get("/api/v1/laptops/", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


def test_free_laptop_appears_in_available_laptops(client, admin_headers):
    # LP-001 is FREE in seed data -> must be available
    avail = _all_available_numbers(client, admin_headers)
    assert "LP-001" in avail


def test_allocated_laptop_disappears_from_available_laptops(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    intern = client.get("/api/v1/interns/", headers=admin_headers).json()[0]
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-001")

    resp = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "ACTIVE"

    # Laptop now ALLOCATED -> must disappear from available list
    avail = _all_available_numbers(client, admin_headers)
    assert "LP-001" not in avail

    # And laptop status should be ALLOCATED in the DB-backed listing
    laptops2 = client.get("/api/v1/laptops/", headers=admin_headers).json()
    lp = next(l for l in laptops2 if l["laptop_number"] == "LP-001")
    assert lp["status"] == "ALLOCATED"


def test_same_laptop_cannot_have_two_active_allocations(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    interns = client.get("/api/v1/interns/", headers=admin_headers).json()
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-002")
    intern_a = next(i for i in interns if i["batch"] == "Morning")
    intern_b = next(i for i in interns if i["batch"] == "Afternoon")

    # First allocation succeeds
    r1 = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern_a["id"],
            "allocation_date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert r1.status_code == 201

    # Second allocation of the SAME laptop (different intern) must be blocked
    r2 = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern_b["id"],
            "allocation_date": "2026-09-10",
            "start_time": "14:00",
            "end_time": "17:00",
        },
    )
    assert r2.status_code == 400
    assert "LP-002" in r2.json()["detail"]

    # Only ONE ACTIVE allocation exists for this laptop
    allocs = client.get("/api/v1/allocations/active", headers=admin_headers).json()
    laptop_allocs = [a for a in allocs if a["laptop_number"] == "LP-002"]
    assert len(laptop_allocs) == 1


def test_morning_allocation_blocks_afternoon_for_same_laptop(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    interns = client.get("/api/v1/interns/", headers=admin_headers).json()
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-003")
    morning = next(i for i in interns if i["batch"] == "Morning")
    afternoon = next(i for i in interns if i["batch"] == "Afternoon")

    # Allocate to Morning intern
    r1 = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": morning["id"],
            "allocation_date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert r1.status_code == 201

    # Same laptop NOT available to Afternoon while Morning allocation is active
    avail = _all_available_numbers(client, admin_headers)
    assert "LP-003" not in avail

    # Attempting to allocate it to an Afternoon intern must fail
    r2 = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": afternoon["id"],
            "allocation_date": "2026-09-10",
            "start_time": "14:00",
            "end_time": "17:00",
        },
    )
    assert r2.status_code == 400
    assert "LP-003" in r2.json()["detail"]


def test_maintenance_and_inactive_laptops_cannot_be_allocated(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    intern = client.get("/api/v1/interns/", headers=admin_headers).json()[0]

    maintenance = next(l for l in laptops if l["laptop_number"] == "LP-019")
    assert maintenance["status"] == "MAINTENANCE"

    # MAINTENANCE laptop must NOT appear in available list
    avail = _all_available_numbers(client, admin_headers)
    assert "LP-019" not in avail

    # Attempting to allocate a MAINTENANCE laptop must fail
    r = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": maintenance["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert r.status_code == 400

    # Change LP-020 to INACTIVE via the API and ensure it's also blocked
    inactive_target = next(l for l in laptops if l["laptop_number"] == "LP-020")
    client.put(f"/api/v1/laptops/{inactive_target['id']}/deactivate", headers=admin_headers)
    laptop_after = client.get(
        f"/api/v1/laptops/{inactive_target['id']}", headers=admin_headers
    ).json()
    assert laptop_after["status"] == "INACTIVE"

    r2 = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": inactive_target["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert r2.status_code == 400


def test_returned_laptop_becomes_free_again(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    intern = client.get("/api/v1/interns/", headers=admin_headers).json()[0]
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-004")

    # Allocate
    r = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert r.status_code == 201
    alloc_id = r.json()["id"]

    # Disappears
    assert "LP-004" not in _all_available_numbers(client, admin_headers)

    # Return the laptop
    ret = client.put(f"/api/v1/allocations/{alloc_id}/return", headers=admin_headers)
    assert ret.status_code == 200
    assert ret.json()["status"] == "RETURNED"

    # Laptop becomes FREE again and reappears in available list
    laptop_after = client.get(f"/api/v1/laptops/{laptop['id']}", headers=admin_headers).json()
    assert laptop_after["status"] == "FREE"
    assert "LP-004" in _all_available_numbers(client, admin_headers)

    # returned_at recorded
    detail = client.get(f"/api/v1/allocations/{alloc_id}", headers=admin_headers).json()
    assert detail["returned_at"] is not None


def test_cancelled_allocation_releases_laptop(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    intern = client.get("/api/v1/interns/", headers=admin_headers).json()[0]
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-005")

    r = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert r.status_code == 201
    alloc_id = r.json()["id"]
    assert "LP-005" not in _all_available_numbers(client, admin_headers)

    # Cancel allocation
    canc = client.put(f"/api/v1/allocations/{alloc_id}/cancel", headers=admin_headers)
    assert canc.status_code == 200
    assert canc.json()["status"] == "CANCELLED"

    # Laptop released -> FREE and available again
    laptop_after = client.get(f"/api/v1/laptops/{laptop['id']}", headers=admin_headers).json()
    assert laptop_after["status"] == "FREE"
    assert "LP-005" in _all_available_numbers(client, admin_headers)


def test_allocation_history_preserved(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    interns = client.get("/api/v1/interns/", headers=admin_headers).json()
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-006")
    intern = next(i for i in interns if i["batch"] == "Morning")

    r = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-11",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert r.status_code == 201
    alloc_id = r.json()["id"]

    # Return it
    client.put(f"/api/v1/allocations/{alloc_id}/return", headers=admin_headers)

    # History retains the record (status still RETURNED, not deleted)
    history = client.get(
        "/api/v1/allocations/history",
        headers=admin_headers,
        params={"page": 1, "page_size": 100},
    ).json()
    assert history["total"] >= 1
    match = [h for h in history["items"] if h["id"] == alloc_id]
    assert len(match) == 1
    assert match[0]["status"] == "RETURNED"
    assert match[0]["laptop_number"] == "LP-006"
    assert match[0]["intern_name"] == intern["name"]

    # History endpoint preserved even after cancellation too
    laptop7 = next(l for l in laptops if l["laptop_number"] == "LP-007")
    intern7 = next(i for i in interns if i["batch"] == "Afternoon")
    r7 = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop7["id"],
            "intern_id": intern7["id"],
            "allocation_date": "2026-09-11",
            "start_time": "14:00",
            "end_time": "17:00",
        },
    )
    client.put(f"/api/v1/allocations/{r7.json()['id']}/cancel", headers=admin_headers)
    history2 = client.get(
        "/api/v1/allocations/history",
        headers=admin_headers,
        params={"status": "CANCELLED", "page_size": 100},
    ).json()
    assert any(h["id"] == r7.json()["id"] for h in history2["items"])
