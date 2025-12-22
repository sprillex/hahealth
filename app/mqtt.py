import os
import json
import logging
import threading
from typing import Any, Dict
import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session
from app import database, models, schemas, auth, services

# Configure logging
logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", None)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "hahealth/log")

class MQTTClient:
    def __init__(self):
        # Use CallbackAPIVersion.VERSION2 for paho-mqtt 2.x compatibility
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def start(self):
        try:
            logger.info(f"Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logger.info("Connected to MQTT Broker!")
            topic = f"{MQTT_TOPIC_PREFIX}/#"
            client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"Failed to connect, return code {reason_code}")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code=None, properties=None):
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

            else:
                logger.warning(f"Unknown data_type: {data_type}")

        except Exception as e:
            logger.error(f"Error processing DB operation: {e}")
        finally:
            db.close()

mqtt_client = MQTTClient()
