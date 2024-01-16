from flask import Flask
from prometheus_client import Counter, generate_latest, REGISTRY, Summary, multiprocess

app = Flask(__name__)

# Define Prometheus metrics
requests_counter = Counter('app_requests_total', 'Total number of requests served by the application')
request_duration_summary = Summary('app_request_duration_seconds', 'Request duration in seconds')

@app.route('/')
@request_duration_summary.time()
def index():
    requests_counter.inc()
    return 'Hello, World!'

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY)

if __name__ == '__main__':
    app.run(threaded=True, port=8080)
