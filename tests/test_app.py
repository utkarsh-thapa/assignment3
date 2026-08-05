from app import create_app


def test_homepage_loads():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Community Volunteer Board" in response.data
