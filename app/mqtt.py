import os
import json
import logging
import threading
import time
from typing import Any, Dict
import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app import database, models, schemas, auth, services

# Configure logging
logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", None)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "hahealth/log")
HASS_DISCOVERY_PREFIX = os.getenv("HASS_DISCOVERY_PREFIX", "homeassistant")

class MQTTClient:
    def __init__(self):
        # Use CallbackAPIVersion.VERSION2 for paho-mqtt 2.x compatibility
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.connected = False
        self._stop_event = threading.Event()
        self._publisher_thread = None

    def get_status(self):
        return {
            "connected": self.connected,
            "broker": MQTT_BROKER,
            "port": MQTT_PORT,
            "username": MQTT_USERNAME or "None",
            "topic_prefix": MQTT_TOPIC_PREFIX,
            "discovery_prefix": HASS_DISCOVERY_PREFIX
        }

    def start(self):
        try:
            logger.info(f"Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()

            # Start background publisher
            self._stop_event.clear()
            self._publisher_thread = threading.Thread(target=self._publisher_loop, daemon=True)
            self._publisher_thread.start()

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def stop(self):
        self._stop_event.set()
        if self._publisher_thread:
            self._publisher_thread.join(timeout=5)
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.connected = True
            logger.info("Connected to MQTT Broker!")
            topic = f"{MQTT_TOPIC_PREFIX}/#"
            client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")

            # Publish discovery immediately on connect
            self._publish_discovery_task()
        else:
            self.connected = False
            logger.error(f"Failed to connect, return code {reason_code}")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code=None, properties=None):
        self.connected = False
        logger.info("Disconnected from MQTT Broker")

    def on_message(self, client, userdata, msg):
        try:
            logger.info(f"Received message on {msg.topic}")
            payload_str = msg.payload.decode()
            data = json.loads(payload_str)

            # Offload processing to a separate thread to prevent blocking the MQTT loop
            threading.Thread(target=self.process_message, args=(data,), daemon=True).start()
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON payload")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def process_message(self, data: Dict[str, Any]):
        # Expecting format:
        # {
        #   "api_key": "...",
        #   "data_type": "...",
        #   "payload": { ... }
        # }

        api_key = data.get("api_key")
        if not api_key:
            logger.warning("Missing api_key in MQTT payload")
            return

        data_type = data.get("data_type")
        if not data_type:
            logger.warning("Missing data_type in MQTT payload")
            return

        inner_payload = data.get("payload")
        if not inner_payload:
            logger.warning("Missing payload object in MQTT data")
            return

        # Create a new DB session
        db = database.SessionLocal()
        try:
            # Verify API Key
            hashed = auth.hash_api_key(api_key)
            key_record = db.query(models.APIKey).filter(
                models.APIKey.hashed_key == hashed,
                models.APIKey.is_active == True
            ).first()

            if not key_record:
                logger.warning("Invalid API Key in MQTT message")
                return

            user = key_record.user
            service_health = services.HealthLogService()
            service_med = services.MedicationService()

            if data_type == schemas.WebhookDataType.BLOOD_PRESSURE:
                bp_data = schemas.BPPayload(**inner_payload)
                service_health.log_bp(db, user.user_id, bp_data)
                logger.info(f"Logged Blood Pressure for user {user.name}")

            elif data_type == schemas.WebhookDataType.MEDICATION_TAKEN:
                med_data = schemas.MedicationTakenPayload(**inner_payload)
                log, alert = service_med.log_dose(
                    db, user.user_id, med_data.med_name, med_data.timestamp, med_window=med_data.med_window
                )
                if alert:
                    logger.warning(f"Medication alert: {alert}")
                logger.info(f"Logged Medication for user {user.name}")

            elif data_type == schemas.WebhookDataType.EXERCISE_SESSION:
                ex_data = schemas.ExercisePayload(**inner_payload)
                service_health.log_exercise(db, user, ex_data)
                logger.info(f"Logged Exercise for user {user.name}")

            elif data_type == schemas.WebhookDataType.FOOD_LOG:
                food_data = schemas.FoodLogPayload(**inner_payload)
                item, error = service_health.log_food(db, user, food_data)
                if error:
                    logger.warning(f"Food log error: {error}")
                else:
                    logger.info(f"Logged Food for user {user.name}")

            elif data_type == schemas.WebhookDataType.WEIGHT:
                weight_data = schemas.WeightPayload(**inner_payload)
                w_kg = weight_data.weight
                if weight_data.unit.lower() in ["lbs", "lb", "pound", "pounds"]:
                    w_kg = w_kg * 0.453592

                user.weight_kg = w_kg
                db.commit()
                logger.info(f"Logged Weight for user {user.name}")

            else:
                logger.warning(f"Unknown data_type: {data_type}")

            # Force a state update after logging new data
            self.publish_periodic_stats(db)

        except Exception as e:
            logger.error(f"Error processing DB operation: {e}")
            db.rollback()
        finally:
            db.close()

    def _publisher_loop(self):
        while not self._stop_event.is_set():
            try:
                db = database.SessionLocal()
                self.publish_periodic_stats(db)
                db.close()
            except Exception as e:
                logger.error(f"Error in publisher loop: {e}")

            # Sleep for 60 seconds or until stopped
            if self._stop_event.wait(60):
                break

    def _publish_discovery_task(self):
        threading.Thread(target=self._publish_discovery_worker, daemon=True).start()

    def _publish_discovery_worker(self):
        db = database.SessionLocal()
        try:
            self.publish_discovery(db)
        except Exception as e:
            logger.error(f"Error publishing discovery: {e}")
        finally:
            db.close()

    def publish_discovery(self, db: Session):
        users = db.query(models.User).all()
        for user in users:
            state_topic = f"hahealth/{user.user_id}/state"
            device_info = {
                "identifiers": [f"hahealth_{user.user_id}"],
                "name": f"Health Tracker: {user.name}",
                "manufacturer": "HAHealth",
                "model": "v1.0"
            }

            sensors = [
                ("weight", "Weight", "weight", "kg"),
                ("bp_systolic", "BP Systolic", None, "mmHg"),
                ("bp_diastolic", "BP Diastolic", None, "mmHg"),
                ("calories_in", "Calories Consumed", "energy", "kcal"),
                ("calories_burned", "Calories Burned", "energy", "kcal")
            ]

            for key, name, device_class, unit in sensors:
                discovery_topic = f"{HASS_DISCOVERY_PREFIX}/sensor/hahealth_{user.user_id}/{key}/config"
                payload = {
                    "name": f"{user.name} {name}",
                    "unique_id": f"hahealth_{user.user_id}_{key}",
                    "state_topic": state_topic,
                    "value_template": f"{{{{ value_json.{key} }}}}",
                    "device_class": device_class,
                    "unit_of_measurement": unit,
                    "device": device_info
                }

                self.client.publish(discovery_topic, json.dumps(payload), retain=True)

    def publish_periodic_stats(self, db: Session):
        users = db.query(models.User).all()
        for user in users:
            try:
                # 1. Profile Stats
                weight = user.weight_kg

                # 2. Daily Log Stats (Calories)
                local_date = services.get_user_local_date(user, None)
                daily = db.query(models.DailyLog).filter(
                    models.DailyLog.user_id == user.user_id,
                    models.DailyLog.date == local_date
                ).first()
                cals_in = daily.total_calories_consumed if daily else 0
                cals_out = daily.total_calories_burned if daily else 0

                # 3. Latest BP
                bp = db.query(models.BloodPressure).filter(
                    models.BloodPressure.user_id == user.user_id
                ).order_by(desc(models.BloodPressure.timestamp)).first()
                systolic = bp.systolic if bp else 0
                diastolic = bp.diastolic if bp else 0

                payload = {
                    "weight": round(weight, 1),
                    "calories_in": cals_in,
                    "calories_burned": cals_out,
                    "bp_systolic": systolic,
                    "bp_diastolic": diastolic
                }

                topic = f"hahealth/{user.user_id}/state"
                self.client.publish(topic, json.dumps(payload), retain=True)

            except Exception as e:
                logger.error(f"Error publishing stats for user {user.name}: {e}")

mqtt_client = MQTTClient()
