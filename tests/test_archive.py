URL = "/api/v1/credits"


def test_archived_credits_leave_the_list_and_the_dashboard(client, create_credit):
    kept = create_credit(client_name="Ana Paz", amount=1000)
    archived = create_credit(client_name="Bruno Diaz", amount=5000)

    response = client.post(f"{URL}/{archived['id']}/archive")

    assert response.status_code == 200
    assert response.get_json()["archived_at"]
    assert [item["id"] for item in client.get(URL).get_json()["items"]] == [kept["id"]]
    assert [item["id"] for item in client.get(f"{URL}?status=archived").get_json()["items"]] == [archived["id"]]
    summary = client.get(f"{URL}/summary").get_json()
    assert (summary["total_credits"], summary["total_amount"]) == (1, "1000.00")


def test_archived_credits_are_read_only(client, create_credit, valid_credit):
    credit = create_credit()
    client.post(f"{URL}/{credit['id']}/archive")

    edit = client.put(f"{URL}/{credit['id']}", json=valid_credit)
    payment = client.post(f"{URL}/{credit['id']}/payments", json={"amount": "10", "paid_on": credit["issue_date"]})

    assert edit.status_code == payment.status_code == 409
    assert edit.get_json()["message"] == "El crédito está archivado. Restáuralo para modificarlo."
    assert client.get(f"{URL}/{credit['id']}").status_code == 200


def test_restoring_brings_the_credit_back(client, create_credit):
    credit = create_credit()
    client.post(f"{URL}/{credit['id']}/archive")

    response = client.post(f"{URL}/{credit['id']}/restore")

    assert response.status_code == 200
    assert response.get_json()["archived_at"] is None
    assert client.get(URL).get_json()["meta"]["total"] == 1
    history = client.get(f"{URL}/{credit['id']}/history").get_json()
    assert [entry["action"] for entry in history] == ["restored", "archived", "created"]


def test_archiving_twice_or_restoring_an_active_credit_is_refused(client, create_credit):
    credit = create_credit()

    assert client.post(f"{URL}/{credit['id']}/restore").status_code == 409
    client.post(f"{URL}/{credit['id']}/archive")
    assert client.post(f"{URL}/{credit['id']}/archive").status_code == 409


def test_only_admins_archive(client_as, create_credit):
    credit = create_credit()

    assert client_as("analyst").post(f"{URL}/{credit['id']}/archive").status_code == 403


# ---------- Editing at the same time ----------

def test_get_sends_the_version_as_etag(client, create_credit):
    credit = create_credit()

    response = client.get(f"{URL}/{credit['id']}")

    assert response.headers["ETag"] == '"1"'
    assert response.get_json()["version"] == 1


def test_each_save_raises_the_version(client, create_credit, valid_credit):
    credit = create_credit()

    response = client.put(f"{URL}/{credit['id']}", json={**valid_credit, "amount": "20000"}, headers={"If-Match": '"1"'})

    assert response.status_code == 200
    assert response.get_json()["version"] == 2
    assert response.headers["ETag"] == '"2"'


def test_saving_an_outdated_version_is_refused(client, create_credit, valid_credit):
    credit = create_credit()
    client.put(f"{URL}/{credit['id']}", json={**valid_credit, "amount": "20000"}, headers={"If-Match": '"1"'})

    # A second person still has version 1 open
    response = client.put(f"{URL}/{credit['id']}", json={**valid_credit, "term_months": 36}, headers={"If-Match": '"1"'})

    assert response.status_code == 412
    assert "Otra persona modificó este crédito" in response.get_json()["message"]
    assert client.get(f"{URL}/{credit['id']}").get_json()["term_months"] == 24


def test_saving_without_if_match_still_works(client, create_credit, valid_credit):
    credit = create_credit()

    assert client.put(f"{URL}/{credit['id']}", json={**valid_credit, "amount": "20000"}).status_code == 200


def test_malformed_if_match_is_refused(client, create_credit, valid_credit):
    credit = create_credit()

    assert client.put(f"{URL}/{credit['id']}", json=valid_credit, headers={"If-Match": "abc"}).status_code == 412
