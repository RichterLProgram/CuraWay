from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaConsumer


BACKEND_ROOT = Path(__file__).resolve().parents[1]
EVENT_DIR = BACKEND_ROOT / "output" / "events"
STATUS_PATH = EVENT_DIR / "status.json"


def main() -> None:
    EVENT_DIR.mkdir(parents=True, exist_ok=True)
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("KAFKA_TOPIC", "healthgrid.events")
    group_id = os.getenv("KAFKA_GROUP_ID", "healthgrid-consumer")

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )

    for message in consumer:
        payload = message.value
        payload["ingested_at"] = datetime.now(timezone.utc).isoformat()
        with (EVENT_DIR / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

        STATUS_PATH.write_text(
            json.dumps(
                {
                    "status": "active",
                    "topic": topic,
                    "last_ingested_at": payload["ingested_at"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
