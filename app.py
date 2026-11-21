"""Flask entry point and HTTP contract for the ScamShield proof of concept."""

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from ml.inference import analyze

MIN_MESSAGE_LENGTH = 3
MAX_MESSAGE_LENGTH = 6_000
MAX_REQUEST_BYTES = 24_000
SECURITY_REVISION = "url-first-2026-11-21"
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)

app = Flask(__name__, static_folder="public/static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES


@app.after_request
def headers(response: Response) -> Response:
    """Apply the same security policy to successful and failed requests."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index() -> str:
    """Render the application without loading the model."""
    return render_template("index.html")


def _check_inference_health() -> None:
    """Exercise the saved model and the existing URL security smoke checks."""
    from ml.inference import get_model

    model = get_model()
    model.predict_proba(["A routine health check message"])
    if analyze("https://echallan.parivahan.gov.in.evil.example")[
        "verdict"
    ] != "Potential Scam":
        raise ValueError("URL security smoke failed")
    if analyze("https://echallan.parivahan.gov.in")[
        "verdict"
    ] != "Needs a Closer Look":
        raise ValueError("Official URL smoke failed")


@app.get("/api/health")
def health() -> tuple[Response, int]:
    """Keep the existing readiness response, including failure semantics."""
    try:
        _check_inference_health()
    except Exception:
        return jsonify(status="model_unavailable", model_ready=False), 503
    return jsonify(
        status="ok",
        model_ready=True,
        security_checks=True,
        security_revision=SECURITY_REVISION,
    ), 200


@app.post("/api/analyze")
def detect() -> tuple[Response, int] | Response:
    """Validate submitted text and return the unchanged analysis contract."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("message"), str):
        return jsonify(error="Send a message as text."), 400
    text = data["message"].strip()
    if not MIN_MESSAGE_LENGTH <= len(text) <= MAX_MESSAGE_LENGTH:
        return jsonify(error="Use between 3 and 6,000 characters."), 400
    try:
        return jsonify(analyze(text))
    except FileNotFoundError:
        return jsonify(
            error=(
                "The trained model is unavailable. "
                "Please finish the offline training step."
            )
        ), 503


@app.errorhandler(413)
def too_large(error: RequestEntityTooLarge) -> tuple[Response, int]:
    """Return the original JSON response for oversized request bodies."""
    return jsonify(error="Message is too large. Use at most 6,000 characters."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
