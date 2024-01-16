from flask import Flask, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Define Prometheus metrics
counter_metric = Counter('flask_requests_total', 'Total number of requests received')
gauge_metric = Gauge('flask_response_time_seconds', 'Response time of the Flask application')

# Define a simple route
@app.route('/')
def hello_world():
    # Increment the counter metric on each request
    counter_metric.inc()

    # Simulate some processing time
    processing_time = 0.5
    gauge_metric.set(processing_time)

    return 'Hello, World!'

# Define a route for Prometheus to scrape metrics
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=5000)

