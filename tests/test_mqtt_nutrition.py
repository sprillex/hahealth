from unittest.mock import MagicMock, patch
import json
import pytest
import datetime
from app import mqtt, models, database, services

def test_mqtt_nutrition_attributes_discovery():
    """Verify that calories_in sensor has json_attributes configuration."""
    user = models.User(user_id=1, name="TestUser", weight_kg=75.0, unit_system="METRIC")
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [user]

    client = mqtt.MQTTClient()
    client.client = MagicMock()

    client.publish_discovery(mock_db)

    # Find calories_in config
    calories_call = None
    for args in client.client.publish.call_args_list:
        if "calories_in/config" in args[0][0]:
            calories_call = args
            break

    assert calories_call is not None
    payload = json.loads(calories_call[0][1])

    # Check for new attributes config
    assert "json_attributes_topic" in payload
    assert payload["json_attributes_topic"] == "hahealth/1/state"
    assert "json_attributes_template" in payload
    assert payload["json_attributes_template"] == "{{ value_json.nutrition | tojson }}"


def test_mqtt_periodic_stats_payload():
    """Verify that periodic stats payload includes nutrition object with correct sums."""
    user = models.User(user_id=1, name="TestUser", weight_kg=75.0, unit_system="METRIC")

    # Mock Date
    today = datetime.date.today()

    # Mock Nutrition Data
    # Item 1: 100g -> 10g Protein, 100mg Calcium
    nut1 = models.NutritionCache(
        food_id=1,
        protein=10.0, calcium=100.0,
        cholesterol=50.0, vitamin_d=10.0
    )
    # Item 2: 200g -> 5g Protein, 50mg Calcium
    nut2 = models.NutritionCache(
        food_id=2,
        protein=5.0, calcium=50.0,
        cholesterol=0.0, vitamin_d=0.0
    )

    # Mock Logs
    # Log 1: 2 servings of Item 1
    log1 = models.FoodItemLog(
        item_log_id=1, user_id=1, food_id=1,
        quantity=2.0, serving_size=1.0,
        timestamp=datetime.datetime.now(),
        nutrition_info=nut1
    )

    # Log 2: 1 serving of Item 2
    log2 = models.FoodItemLog(
        item_log_id=2, user_id=1, food_id=2,
        quantity=1.0, serving_size=1.0,
        timestamp=datetime.datetime.now(),
        nutrition_info=nut2
    )

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [user] # For user query

    # We need to mock the food_logs query inside the loop
    # The code queries: db.query(models.FoodItemLog).filter(...).all()
    # Since we can't easily mock chained calls with specific filters on a generic mock without side effects,
    # we'll mock the return value of the second query call or similar.
    # Actually, the code does:
    # users = db.query(models.User).all() -> returns [user]
    # daily = db.query(models.DailyLog)...first()
    # food_logs = db.query(models.FoodItemLog)...all()
    # bp = db.query(models.BloodPressure)...first()

    # Let's set up the side_effects for the query calls.
    # 1. User query
    # 2. DailyLog query
    # 3. FoodItemLog query
    # 4. BP query

    # However, chained mocks are tricky. Let's simplify by creating a specific mock for db.query

    def query_side_effect(model):
        m = MagicMock()
        if model == models.User:
            m.all.return_value = [user]
            return m
        elif model == models.DailyLog:
            m.filter.return_value.first.return_value = None
            return m
        elif model == models.FoodItemLog:
            m.filter.return_value.all.return_value = [log1, log2]
            return m
        elif model == models.BloodPressure:
            m.filter.return_value.order_by.return_value.first.return_value = None
            return m
        return m

    mock_db.query.side_effect = query_side_effect

    # Mock services.get_user_local_date to always return today
    with patch("app.services.get_user_local_date", return_value=today):
        client = mqtt.MQTTClient()
        client.client = MagicMock()

        client.publish_periodic_stats(mock_db)

        # Verify Publish
        args = client.client.publish.call_args
        topic, payload_str = args[0][0], args[0][1]

        assert topic == "hahealth/1/state"
        payload = json.loads(payload_str)

        # Check Nutrition Object
        assert "nutrition" in payload
        nut = payload["nutrition"]

        # Calculation:
        # Protein: (10 * 2) + (5 * 1) = 25.0
        # Calcium: (100 * 2) + (50 * 1) = 250.0
        # Cholesterol: (50 * 2) + (0 * 1) = 100.0
        # Vitamin D: (10 * 2) + (0 * 1) = 20.0

        assert nut["protein"] == 25.0
        assert nut["calcium"] == 250.0
        assert nut["cholesterol"] == 100.0
        assert nut["vitamin_d"] == 20.0
