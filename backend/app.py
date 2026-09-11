"""
Admission Guru — Flask Backend
"""

import os
import sys

# Make backend importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

import auth
import predictor
import pdf_gen
from data_parser import get_meta


# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "frontend")
)

app = Flask(
    __name__,
    static_folder=None,   # Disable Flask's built-in static serving — we handle it via routes
)

# Allow frontend to communicate with Flask
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True
)

# Initialize database
auth.init_db()


# ─────────────────────────────────────────────────────────────────────────────
# Authentication helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_current_user():
    token = request.headers.get("Authorization", "")

    if token.startswith("Bearer "):
        token = token[7:].strip()

    if not token:
        return None, "No token"

    payload, err = auth.decode_token(token)

    return payload, err


def require_auth():
    payload, err = get_current_user()

    if err or not payload:
        return None, (
            jsonify({
                "error": err or "Unauthorized"
            }),
            401
        )

    return payload, None


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "message": "Admission Guru Flask server is running",
        "status": "online"
    })


@app.route("/health", methods=["GET"])
def health_simple():
    """Simple health check that avoids any routing conflicts."""
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────────────────────────────────────────
# Serve frontend
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    # Hard-stop: never intercept /api/* paths — let Flask's proper API routes handle them
    if path.startswith("api/") or path == "api":
        from flask import abort
        abort(404)

    full_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIR, path)

    # SPA fallback for frontend routing
    return send_from_directory(FRONTEND_DIR, "index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Authentication routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    phone = data.get("phone", "").strip()

    if not name or not email or not password:
        return jsonify({
            "error": "Name, email and password are required"
        }), 400

    if len(password) < 6:
        return jsonify({
            "error": "Password must be at least 6 characters"
        }), 400

    user, err = auth.register_user(
        name,
        email,
        password,
        phone
    )

    if err:
        return jsonify({
            "error": err
        }), 409

    return jsonify({
        "success": True,
        "user": user
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    user, err = auth.login_user(
        email,
        password
    )

    if err:
        return jsonify({
            "error": err
        }), 401

    return jsonify({
        "success": True,
        "user": user
    })


@app.route("/api/auth/me", methods=["GET"])
def me():
    payload, resp = require_auth()

    if resp:
        return resp

    user = auth.get_user(
        payload["user_id"]
    )

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    return jsonify({
        "user": user
    })


# ─────────────────────────────────────────────────────────────────────────────
# Meta / dropdown data
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/meta/<exam_type>", methods=["GET"])
def meta(exam_type):

    valid = [
        "CET",
        "Pharmacy",
        "DSY_Engineering",
        "Diploma",
        "DSY_Pharmacy"
    ]

    if exam_type not in valid:
        return jsonify({
            "error": "Invalid exam type"
        }), 400

    data = get_meta(exam_type)

    return jsonify(data)


# ─────────────────────────────────────────────────────────────────────────────
# Prediction
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/predict", methods=["POST"])
def predict():

    params = request.get_json(silent=True) or {}

    if not params.get("exam_type"):
        return jsonify({
            "error": "exam_type is required"
        }), 400

    try:
        results = predictor.predict(params)

        return jsonify({
            "count": len(results),
            "results": results
        })

    except Exception as e:
        print("Prediction error:", e)

        return jsonify({
            "error": "Prediction failed",
            "details": str(e)
        }), 500


# ─────────────────────────────────────────────────────────────────────────────
# PDF Download
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/pdf", methods=["POST"])
def download_pdf():

    data = request.get_json(silent=True) or {}

    results = data.get("results", [])
    input_summary = data.get("input_summary", {})
    exam_type = data.get("exam_type", "")

    try:
        buf = pdf_gen.generate_pdf(
            results,
            input_summary,
            exam_type
        )

        return send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="AdmissionGuru_CollegeList.pdf"
        )

    except Exception as e:
        print("PDF generation error:", e)

        return jsonify({
            "error": "PDF generation failed",
            "details": str(e)
        }), 500


# ─────────────────────────────────────────────────────────────────────────────
# Saved lists
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/lists", methods=["GET"])
def get_lists():

    payload, resp = require_auth()

    if resp:
        return resp

    lists = auth.get_saved_lists(
        payload["user_id"]
    )

    return jsonify({
        "lists": lists
    })


@app.route("/api/lists", methods=["POST"])
def save_list():

    payload, resp = require_auth()

    if resp:
        return resp

    data = request.get_json(silent=True) or {}

    exam_type = data.get("exam_type", "")
    input_summary = data.get("input_summary", {})
    results = data.get("results", [])

    list_id = auth.save_list(
        payload["user_id"],
        exam_type,
        input_summary,
        results
    )

    return jsonify({
        "success": True,
        "id": list_id
    }), 201


@app.route("/api/lists/<int:list_id>", methods=["DELETE"])
def delete_list(list_id):

    payload, resp = require_auth()

    if resp:
        return resp

    ok = auth.delete_saved_list(
        payload["user_id"],
        list_id
    )

    if not ok:
        return jsonify({
            "error": "List not found"
        }), 404

    return jsonify({
        "success": True
    })


# ─────────────────────────────────────────────────────────────────────────────
# Error handlers
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Route not found",
        "path": request.path
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error"
    }), 500


# ─────────────────────────────────────────────────────────────────────────────
# Run server
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 60)
    print("Admission Guru — Flask Backend")
    print("=" * 60)
    print(f"Frontend directory: {FRONTEND_DIR}")
    print("Server: http://localhost:5000")
    print("Health: http://localhost:5000/api/health")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )