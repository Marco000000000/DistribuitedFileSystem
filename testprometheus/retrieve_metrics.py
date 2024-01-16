from prometheus_api_client import PrometheusConnect
from time import sleep

prometheus_url = "http://prometheus:9090"
prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)

def query():
    # Query for a specific metric
    query = 'flask_requests_total'

    # Get the metric data
    metric_data = prometheus.custom_query(query)

    print(f"Metric data for {query}: {metric_data}")


if __name__ == '__main__':
    query()
    sleep(25)
    query()