"""Tests for dashboard statistics, history pagination/filters, reports, CSV export and schema validation."""


def test_dashboard_stats_kpis(client, admin_headers):
    stats = client.get("/api/v1/dashboard/stats", headers=admin_headers).json()
    assert stats["total_laptops"] == 20
    assert stats["total_interns"] == 10
    assert stats["maintenance_laptops"] == 1
    assert stats["allocated_laptops"] == 0
    assert stats["morning_allocations"] == 0
    assert stats["afternoon_allocations"] == 0
    # Laptop status distribution sums to total laptops
    assert sum(d["value"] for d in stats["laptop_status_distribution"]) == stats["total_laptops"]
    # Batch allocation chart has Morning, Afternoon and Full Day
    assert {b["name"] for b in stats["batch_allocations"]} == {"Morning", "Afternoon", "Full Day"}


def test_history_pagination_and_empty_state(client, admin_headers):
    h = client.get(
        "/api/v1/allocations/history",
        headers=admin_headers,
        params={"page": 1, "page_size": 10},
    ).json()
    assert h["total"] == 0
    assert h["total_pages"] == 0
    assert h["items"] == []

    # page_size respected and shape correct
    assert isinstance(h["items"], list)
    assert "page" in h and "page_size" in h


def test_history_filters(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    interns = client.get("/api/v1/interns/", headers=admin_headers).json()
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-008")
    morning = next(i for i in interns if i["batch"] == "Morning")
    afternoon = next(i for i in interns if i["batch"] == "Afternoon")

    # Create two allocations: one morning, one afternoon on different dates
    for lap, intern, date_, start, end in [
        (laptop["id"], morning["id"], "2026-09-12", "09:00", "12:00"),
    ]:
        assert client.post(
            "/api/v1/allocations/",
            headers=admin_headers,
            json={
                "laptop_id": lap,
                "intern_id": intern,
                "allocation_date": date_,
                "start_time": start,
                "end_time": end,
            },
        ).status_code == 201

    laptop_b = next(l for l in laptops if l["laptop_number"] == "LP-009")
    assert client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop_b["id"],
            "intern_id": afternoon["id"],
            "allocation_date": "2026-09-13",
            "start_time": "14:00",
            "end_time": "17:00",
        },
    ).status_code == 201

    # filter by batch
    h = client.get(
        "/api/v1/allocations/history", headers=admin_headers,
        params={"batch": "Morning", "page_size": 100},
    ).json()
    assert h["total"] == 1
    assert all(x["batch"] == "Morning" for x in h["items"])

    # filter by date
    hd = client.get(
        "/api/v1/allocations/history", headers=admin_headers,
        params={"allocation_date": "2026-09-12", "page_size": 100},
    ).json()
    assert hd["total"] == 1

    # filter by status ACTIVE
    hs = client.get(
        "/api/v1/allocations/history", headers=admin_headers,
        params={"status": "ACTIVE", "page_size": 100},
    ).json()
    assert hs["total"] == 2

    # search by laptop number
    ss = client.get(
        "/api/v1/allocations/history", headers=admin_headers,
        params={"search": "LP-008", "page_size": 100},
    ).json()
    assert ss["total"] == 1


def test_reports_summary(client, admin_headers):
    rep = client.get("/api/v1/allocations/reports", headers=admin_headers).json()
    assert rep["total_allocations"] >= 0
    assert rep["total_interns"] == 10
    assert rep["total_laptops"] == 20
    # domain totals add up to total (sum of all domains)
    assert sum(d["total_allocations"] for d in rep["domain_stats"]) == rep["total_allocations"]


def test_csv_export(client, admin_headers):
    r = client.get("/api/v1/allocations/export", headers=admin_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    # header row present
    lines = r.text.strip().splitlines()
    assert "Laptop,Intern,Batch,Domain,Allocation Date,Start Time,End Time,Status" in lines[0]


def test_allocation_time_validation(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    intern = client.get("/api/v1/interns/", headers=admin_headers).json()[0]
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-010")
    r = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-12",
            "start_time": "12:00",
            "end_time": "09:00",
        },
    )
    assert r.status_code == 400
    assert "End time" in r.json()["detail"]


def test_duplicate_laptop_number_rejected(client, admin_headers):
    r = client.post(
        "/api/v1/laptops/",
        headers=admin_headers,
        json={
            "laptop_number": "LP-001",
            "brand": "X",
            "model": "Y",
            "serial_number": "SN-DUP-999",
            "status": "FREE",
        },
    )
    assert r.status_code == 400
    assert "already exists" in r.json()["detail"]


def test_laptop_validation_missing_fields(client, admin_headers):
    r = client.post(
        "/api/v1/laptops/",
        headers=admin_headers,
        json={"laptop_number": "LP-050"},
    )
    assert r.status_code == 422


def test_intern_invalid_domain_rejected(client, admin_headers):
    r = client.post(
        "/api/v1/interns/",
        headers=admin_headers,
        json={
            "intern_id": "INT-099",
            "name": "Test",
            "email": "t@test.com",
            "phone": "9999999999",
            "batch": "Morning",
            "domain": "Not A Real Domain",
        },
    )
    assert r.status_code == 422


def test_full_day_batch_workflow(client, admin_headers):
    # Create a Full Day intern
    r = client.post(
        "/api/v1/interns/",
        headers=admin_headers,
        json={
            "intern_id": "INT-098",
            "name": "Full Day Intern",
            "email": "full.day@interns.com",
            "phone": "9999999998",
            "batch": "Full Day",
            "domain": "Cloud",
        },
    )
    assert r.status_code == 201
    assert r.json()["batch"] == "Full Day"

    # Batch summary counts include it
    summary = client.get("/api/v1/interns/summary", headers=admin_headers).json()
    assert summary["total"] == 11
    assert summary["morning"] == 6
    assert summary["afternoon"] == 4
    assert summary["full_day"] == 1

    # Allocating a laptop records the Full Day batch on the allocation
    laptop = next(l for l in client.get("/api/v1/laptops/", headers=admin_headers).json() if l["laptop_number"] == "LP-011")
    alloc = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": r.json()["id"],
            "allocation_date": "2026-09-15",
            "start_time": "09:00",
            "end_time": "18:00",
        },
    )
    assert alloc.status_code == 201
    assert alloc.json()["batch"] == "Full Day"

    # Dashboard reports the Full Day allocation
    stats = client.get("/api/v1/dashboard/stats", headers=admin_headers).json()
    assert stats["full_day_allocations"] == 1
    assert any(
        b["name"] == "Full Day" and b["value"] == 1 for b in stats["batch_allocations"]
    )

    rep = client.get("/api/v1/allocations/reports", headers=admin_headers).json()
    assert rep["full_day_allocations"] == 1

    # History batch filter works for Full Day
    h = client.get(
        "/api/v1/allocations/history",
        headers=admin_headers,
        params={"batch": "Full Day", "page_size": 100},
    ).json()
    assert h["total"] == 1
    assert all(x["batch"] == "Full Day" for x in h["items"])
