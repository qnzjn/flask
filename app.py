from flask import Flask, jsonify, render_template, request

from govfeed.collector import get_feed

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", feed=get_feed())


@app.route("/api/gov-feed")
def gov_feed_api():
    feed = get_feed()
    cat = (request.args.get("cat") or "").strip()
    if not cat:
        return jsonify(feed)
    sections = [s for s in feed["sections"] if s["id"] == cat]
    items = [item for item in feed["items"] if item["cat"] == cat]
    return jsonify({**feed, "sections": sections, "items": items})
