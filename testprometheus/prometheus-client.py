from flask import Flask, request
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from time import sleep, time

app = Flask(__name__)

# Define Prometheus metrics
REQUEST_COUNTER = Counter('flask_app_request_count', 'Total number of requests')
REQUEST_DURATION = Histogram('flask_app_request_duration_seconds', 'Request duration in seconds')

# Flask middleware to measure request duration
@app.before_request
def before_request():
    request.start_time = time()

@app.after_request
def after_request(response):
    duration = time() - request.start_time
    REQUEST_COUNTER.inc()
    REQUEST_DURATION.observe(duration)
    return response

# Endpoint to expose Prometheus metrics
@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY)

# Your main endpoint where you want to measure the time spent
@app.route('/')
def your_function():
    with REQUEST_DURATION.time():
        # Your function logic here
        sleep(1)  # Simulating some work
    
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
