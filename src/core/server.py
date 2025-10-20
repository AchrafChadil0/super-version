import json
import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS
from livekit import api

app = Flask(__name__)
CORS(app)  # Enable CORS for all routesse

# Your LiveKit credentials

LIVEKIT_API_KEY = "APIqrFbzXutaCZn"
LIVEKIT_API_SECRET = "N6ANet5dU1HG84oAbVhxlUNam7CEHogg0Ip1oovKqcI"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/generate-token", methods=["POST"])
def generate_token():
    try:
        # Parse the incoming JSON data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        # Get parameters from query string or use defaults
        room_name = f"room-{uuid.uuid4().hex[:7]}"
        identity = f"user-{uuid.uuid4().hex[:7]}"

        # Create token with room-specific settings
        import datetime

        token = (
            api.AccessToken()
            .with_identity(identity)
            .with_name(identity)
            .with_room_config(
                api.RoomConfiguration(
                    name=room_name,
                    max_participants=1,
                    agents=[
                        api.RoomAgentDispatch(
                            metadata=json.dumps(data),
                        )
                    ],
                )
            )
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .with_ttl(datetime.timedelta(seconds=24 * 60 * 60))
        )  # 24 hours

        jwt_token = token.to_jwt()

        print(f"Generated token for room: {room_name}, identity: {identity}")

        return jsonify({"token": jwt_token, "room": room_name, "identity": identity})

    except Exception as e:
        print(f"Error generating token: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting LiveKit Token Server...")
    print("Server will run on http://127.0.0.1:8000")
    app.run(
        host="0.0.0.0", port=8000, debug=False
    )  # Changed host and disabled debug for production
