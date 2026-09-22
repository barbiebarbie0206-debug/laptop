"""Tests for the enhanced laptops search (laptop + intern + allocation related data)."""


def _allocated_laptop(client, admin_headers):
    """Create an allocation for LP-008 (Aarav Sharma / INT-001) and return its laptop id."""
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    laptop = next(l for l in laptops if l["laptop_number"] == "LP-008")
    interns = client.get("/api/v1/interns/", headers=admin_headers).json()
    intern = next(i for i in interns if i["intern_id"] == "INT-001")
    resp = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-12",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert resp.status_code == 201, resp.text
    return laptop["id"], resp.json()["id"]


def _allocate(intern_id, laptop_number, client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    laptop = next(l for l in laptops if l["laptop_number"] == laptop_number)
    interns = client.get("/api/v1/interns/", headers=admin_headers).json()
    intern = next(i for i in interns if i["intern_id"] == intern_id)
    resp = client.post(
        "/api/v1/allocations/",
        headers=admin_headers,
        json={
            "laptop_id": laptop["id"],
            "intern_id": intern["id"],
            "allocation_date": "2026-09-12",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )
    assert resp.status_code == 201, resp.text


def test_search_by_laptop_id(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "LP-013", "envelope": True})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["laptop_number"] == "LP-013"
    assert item["serial_number"] == "LN-T14-003"
    assert item["current_intern"] is None


def test_search_by_serial_number(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "DL-5520-001"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["laptop_number"] == "LP-001"


def test_search_is_case_insensitive_and_partial(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "elitebook"})
    items = r.json()
    assert len(items) == 4
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "AC-A5-002"})
    assert len(r.json()) == 1


def test_search_by_intern_id_returns_allocated_laptop(client, admin_headers):
    laptop_id, _ = _allocated_laptop(client, admin_headers)
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "INT-001", "envelope": True})
    body = r.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == laptop_id
    assert item["laptop_number"] == "LP-008"
    assert item["status"] == "ALLOCATED"
    assert item["current_intern"] is not None
    assert item["current_intern"]["intern_id"] == "INT-001"
    assert item["current_intern"]["name"] == "Aarav Sharma"
    assert item["current_intern"]["domain"] == "Full Stack"
    assert item["current_intern"]["batch"] == "Morning"
    assert item["allocation_id"] is not None


def test_search_by_intern_name(client, admin_headers):
    laptop_id, _ = _allocated_laptop(client, admin_headers)
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "aarav"})
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == laptop_id


def test_search_by_intern_email(client, admin_headers):
    laptop_id, _ = _allocated_laptop(client, admin_headers)
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "AARAV.SHARMA@INTERNS.COM"})
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == laptop_id


def test_search_by_domain(client, admin_headers):
    laptop_id, _ = _allocated_laptop(client, admin_headers)
    # Display value ("Full Stack") and stored enum name ("FULL_STACK") must both work
    for term in ("full stack", "FULL_STACK", "Full St"):
        r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": term})
        items = r.json()
        assert len(items) == 1, f"term={term!r}"
        assert items[0]["id"] == laptop_id, f"term={term!r}"


def test_search_by_allocation_id(client, admin_headers):
    laptop_id, allocation_id = _allocated_laptop(client, admin_headers)
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": str(allocation_id)})
    items = r.json()
    # The allocated laptop must be among the (substring-matching) results
    allocated = next((i for i in items if i["id"] == laptop_id), None)
    assert allocated is not None
    assert allocated["allocation_id"] == allocation_id


def test_search_invalid_intern_id_returns_nothing(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "INT-999", "envelope": True})
    body = r.json()
    assert body["items"] == []
    assert body["intern_without_laptop"] is False


def test_search_intern_without_laptop_shows_empty_state(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "INT-002", "envelope": True})
    body = r.json()
    assert body["items"] == []
    assert body["intern_without_laptop"] is True


def test_search_intern_by_name_without_laptop(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "priya", "envelope": True})
    body = r.json()
    assert body["items"] == []
    assert body["intern_without_laptop"] is True


def test_search_and_status_filter_work_together(client, admin_headers):
    _allocated_laptop(client, admin_headers)
    # Matching intern + matching status -> laptop returned
    r = client.get(
        "/api/v1/laptops/",
        headers=admin_headers,
        params={"search": "INT-001", "status": "ALLOCATED", "envelope": True},
    )
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["laptop_number"] == "LP-008"
    # Same search with a conflicting status -> empty, but intern has a laptop
    r = client.get(
        "/api/v1/laptops/",
        headers=admin_headers,
        params={"search": "INT-001", "status": "FREE", "envelope": True},
    )
    body = r.json()
    assert body["items"] == []
    assert body["intern_without_laptop"] is False


def test_no_search_returns_all_laptops(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 20


def test_default_list_response_is_still_an_array(client, admin_headers):
    r = client.get("/api/v1/laptops/", headers=admin_headers)
    assert isinstance(r.json(), list)


def test_get_single_laptop_includes_current_intern(client, admin_headers):
    laptop_id, _ = _allocated_laptop(client, admin_headers)
    r = client.get(f"/api/v1/laptops/{laptop_id}", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["current_intern"] is not None
    assert body["current_intern"]["intern_id"] == "INT-001"


def test_search_by_batch(client, admin_headers):
    laptop_id, _ = _allocated_laptop(client, admin_headers)
    _allocate("INT-003", "LP-009", client, admin_headers)  # Karthik-free afternoon intern -> LP-009
    for term in ("morning", "MORNING", "Morn"):
        r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": term})
        ids = [i["id"] for i in r.json()]
        assert laptop_id in ids, f"term={term!r}"
        assert all(i["current_intern"]["batch"] == "Morning" for i in r.json()), f"term={term!r}"
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "afternoon"})
    items = r.json()
    assert len(items) == 1
    assert items[0]["current_intern"]["batch"] == "Afternoon"


def test_search_by_status(client, admin_headers):
    laptop_id, _ = _allocated_laptop(client, admin_headers)
    r = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "allocated"})
    items = r.json()
    assert any(i["id"] == laptop_id for i in items)
    assert all(i["status"] == "ALLOCATED" for i in items)


def test_filter_by_returned_status(client, admin_headers):
    laptops = client.get("/api/v1/laptops/", headers=admin_headers).json()
    lap = next(l for l in laptops if l["laptop_number"] == "LP-005")
    r = client.put(f"/api/v1/laptops/{lap['id']}/status", headers=admin_headers, json={"status": "RETURNED"})
    assert r.status_code == 200
    # Status filter works
    fr = client.get("/api/v1/laptops/", headers=admin_headers, params={"status": "RETURNED", "envelope": True})
    body = fr.json()
    assert [i["laptop_number"] for i in body["items"]] == ["LP-005"]
    # Status is searchable too
    sr = client.get("/api/v1/laptops/", headers=admin_headers, params={"search": "returned"})
    assert [i["laptop_number"] for i in sr.json()] == ["LP-005"]