from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

from src.demand.profile_extractor import extract_demand_from_text
from src.supply.facility_parser import parse_facility_document


app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "HealthGrid AI"})


@app.route("/parse/demand", methods=["POST"])
def parse_demand():
    """Parse patient report, return demand requirements."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    result = extract_demand_from_text(text)
    return jsonify(result.model_dump())


@app.route("/parse/supply", methods=["POST"])
def parse_supply():
    """Parse facility doc, return capabilities."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    result = parse_facility_document(text)
    return jsonify(result.model_dump())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

from src.demand.profile_extractor import extract_demand_from_text
from src.supply.facility_parser import parse_facility_document


app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "HealthGrid AI"})


@app.route("/parse/demand", methods=["POST"])
def parse_demand():
    """Parse patient report, return demand requirements."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    result = extract_demand_from_text(text)
    return jsonify(result.model_dump())


@app.route("/parse/supply", methods=["POST"])
def parse_supply():
    """Parse facility doc, return capabilities."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    result = parse_facility_document(text)
    return jsonify(result.model_dump())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
