import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.battery_simulator import BatteryFleetSimulator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VoltWatch battery telemetry simulator")
    parser.add_argument("--api-url", default="http://localhost:5000", help="Flask API base URL")
    parser.add_argument("--mqtt-broker", default="broker.hivemq.com", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument(
        "--mqtt-topic",
        default="voltwatch/battery/telemetry",
        help="MQTT topic for telemetry",
    )
    parser.add_argument("--battery-count", type=int, default=10, help="Number of batteries to simulate (minimum 10)")
    parser.add_argument("--device-prefix", default="battery_pack_", help="Device ID prefix (e.g. battery_pack_)")
    parser.add_argument("--interval", type=int, default=5, help="Telemetry interval in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    battery_count = max(10, args.battery_count)
    if args.battery_count < 10:
        print("Requested battery count is below 10. Using minimum of 10 batteries.")

    simulator = BatteryFleetSimulator(
        api_url=args.api_url,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_topic=args.mqtt_topic,
        battery_count=battery_count,
        device_prefix=args.device_prefix,
    )
    simulator.run_forever(interval_seconds=args.interval)


if __name__ == "__main__":
    main()
