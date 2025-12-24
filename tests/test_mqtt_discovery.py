from unittest.mock import MagicMock, patch
import json
import pytest
from app import mqtt, models, database

@pytest.fixture
def mock_mqtt_client():
    with patch("app.mqtt.MQTTClient.publish_discovery") as mock_publish:
        yield mock_publish

@pytest.fixture
def mock_db_session():
    # Create a mock session that behaves like a SQLAlchemy session
    session = MagicMock(spec=database.SessionLocal)
    return session

def test_mqtt_discovery_payload_generation():
    # 1. Setup Mock User
    user = models.User(
        user_id=1,
        name="TestUser",
        weight_kg=75.0,
        height_cm=180.0,
        unit_system="METRIC",
        is_admin=False
    )

    # 2. Setup Mock DB
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [user]

    # 3. Instantiate MQTTClient (avoid connecting)
    client = mqtt.MQTTClient()
    client.client = MagicMock() # Mock the paho client

    # 4. Run publish_discovery
    client.publish_discovery(mock_db)

    # 5. Verify calls
    # We expect 5 sensors: Weight, BP Systolic, BP Diastolic, Cals In, Cals Out
    assert client.client.publish.call_count == 5

    # Check one payload specifically (Weight)
    call_args_list = client.client.publish.call_args_list

    # Find weight config topic
    weight_call = None
    for args in call_args_list:
        if "weight/config" in args[0][0]:
            weight_call = args
            break

    assert weight_call is not None
    topic, payload, retain = weight_call[0][0], weight_call[0][1], weight_call[1].get('retain', False) or weight_call[0][2] if len(weight_call[0]) > 2 else False

    data = json.loads(payload)
    assert data["name"] == "TestUser Weight"
    assert data["unique_id"] == "hahealth_1_weight"
    assert data["unit_of_measurement"] == "kg"
    assert data["device_class"] == "weight"
    assert data["device"]["identifiers"] == ["hahealth_1"]

def test_mqtt_discovery_payload_imperial():
    # 1. Setup Mock User with Imperial
    user = models.User(
        user_id=2,
        name="ImperialUser",
        weight_kg=75.0,
        unit_system="IMPERIAL"
    )

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [user]

    client = mqtt.MQTTClient()
    client.client = MagicMock()

    client.publish_discovery(mock_db)

    # Check Weight Unit
    weight_call = None
    for args in client.client.publish.call_args_list:
        if "weight/config" in args[0][0]:
            weight_call = args
            break

    assert weight_call is not None
    payload = json.loads(weight_call[0][1])
    assert payload["unit_of_measurement"] == "lb"
