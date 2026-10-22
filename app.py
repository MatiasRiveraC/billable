import os
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, render_template, abort

load_dotenv()  # reads .env when run without Docker; real environment variables take precedence

app = Flask(__name__)

FACTURAS_DIR = Path(os.environ.get("FACTURAS_DIR", Path(__file__).parent / "facturas"))

# Invoice defaults shown in the UI ("Emisor / Cliente / Pago"), read from the environment (.env).
INFO_ENV = {
    "emitterName": "EMITTER_NAME",
    "emitterRut": "EMITTER_TAX_ID",
    "emitterEmail": "EMITTER_EMAIL",
    "clientName": "CLIENT_NAME",
    "clientAddress": "CLIENT_ADDRESS",
    "bank": "BANK_NAME",
    "accountType": "BANK_ACCOUNT_TYPE",
    "accountNumber": "BANK_ACCOUNT_NUMBER",
    "accountHolder": "BANK_ACCOUNT_HOLDER",
    "accountRut": "BANK_ACCOUNT_HOLDER_TAX_ID",
    "defaultRate": "DEFAULT_HOURLY_RATE",
}


def ensure_dir():
    FACTURAS_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["GET"])
def get_info():
    """Invoice defaults (issuer, client, payment details) from the environment."""
    return jsonify({key: os.environ.get(env, "") for key, env in INFO_ENV.items()})


@app.route("/api/facturas", methods=["GET"])
def list_facturas():
    """List all saved facturas with metadata."""
    ensure_dir()
    facturas = []
    for f in sorted(FACTURAS_DIR.glob("*.pdf"), reverse=True):
        stat = f.stat()
        # Try to extract metadata from filename: Factura_Mes_Año_NNN.pdf
        name = f.stem  # e.g. Factura_Marzo_2026_008
        facturas.append({
            "filename": f.name,
            "size": stat.st_size,
            "saved_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
        })
    return jsonify(facturas)


@app.route("/api/facturas", methods=["POST"])
def save_factura():
    """Save a PDF factura sent as binary."""
    ensure_dir()
    filename = request.headers.get("X-Filename", "").strip()
    if not filename:
        return jsonify({"error": "Missing X-Filename header"}), 400

    # Sanitize filename
    filename = re.sub(r'[^\w\-_\. ]', '_', filename)
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    dest = FACTURAS_DIR / filename
    # If file exists, add a suffix to avoid silent overwrite
    if dest.exists():
        stem = dest.stem
        dest = FACTURAS_DIR / f"{stem}_dup_{int(datetime.now().timestamp())}.pdf"

    dest.write_bytes(request.data)
    return jsonify({"ok": True, "saved_as": dest.name}), 201


@app.route("/api/facturas/<filename>", methods=["GET"])
def download_factura(filename):
    """Download a saved factura PDF."""
    ensure_dir()
    # Sanitize
    filename = re.sub(r'[^\w\-_\. ]', '_', filename)
    path = FACTURAS_DIR / filename
    if not path.exists() or not path.is_file():
        abort(404)
    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=request.args.get("download") == "1",
        download_name=filename,
    )


@app.route("/api/facturas/<filename>", methods=["DELETE"])
def delete_factura(filename):
    """Delete a saved factura."""
    filename = re.sub(r'[^\w\-_\. ]', '_', filename)
    path = FACTURAS_DIR / filename
    if not path.exists():
        abort(404)
    path.unlink()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
