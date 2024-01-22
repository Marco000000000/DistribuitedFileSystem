from flask import Flask
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY, Gauge
from prometheus_client.exposition import CONTENT_TYPE_LATEST

app = Flask(__name__)

# Define some example metrics
counter = Counter('my_flask_app_requests_total', 'Total number of requests received')
histogram = Histogram('my_flask_app_request_duration_seconds', 'Duration of requests in seconds')
gauge = Gauge('my_flask_app_active_users', 'Number of active users')

# Define a route that updates metrics
@app.route('/process')
def process():
    # Update metrics
    counter.inc()
    histogram.observe(1.5)  # Simulate a request duration of 1.5 seconds
    gauge.set(42)  # Simulate 42 active users

    return 'Processing request'

# Define a route for Prometheus to scrape metrics
@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
