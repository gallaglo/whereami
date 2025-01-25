from flask import Flask, render_template, request, Response, jsonify
import logging
from logging.config import dictConfig
from google import genai
from google.genai import types
import markdown
import json
import sys
import os
from flask_cors import CORS
import whereami_payload
from concurrent import futures
import multiprocessing
import grpc
from grpc_reflection.v1alpha import reflection
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
import whereami_pb2
import whereami_pb2_grpc
from prometheus_flask_exporter import PrometheusMetrics
from py_grpc_prometheus.prometheus_server_interceptor import PromServerInterceptor
from prometheus_client import start_http_server

os.environ["OTEL_PYTHON_FLASK_EXCLUDED_URLS"] = "healthz,metrics"
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

host_ip = os.getenv("HOST", "0.0.0.0")

trace_sampling_ratio = 0
if os.getenv("TRACE_SAMPLING_RATIO"):
    try:
        trace_sampling_ratio = float(os.getenv("TRACE_SAMPLING_RATIO"))
    except:
        logging.warning("Invalid trace ratio provided.")

if trace_sampling_ratio > 0:
    logging.info("Attempting to enable tracing.")
    sampler = TraceIdRatioBased(trace_sampling_ratio)
    set_global_textmap(CloudTraceFormatPropagator())
    tracer_provider = TracerProvider(sampler=sampler)
    cloud_trace_exporter = CloudTraceSpanExporter()
    tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer(__name__)
    logging.info("Tracing enabled.")
else:
    logging.info("Tracing disabled.")

app = Flask(__name__)
handler = logging.StreamHandler(sys.stdout)
app.logger.addHandler(handler)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
app.config['JSON_AS_ASCII'] = False
CORS(app)
metrics = PrometheusMetrics(app)

grpc_serving_port = int(os.environ.get('PORT', 9090))
grpc_metrics_port = 8000

whereami_payload = whereami_payload.WhereamiPayload()

class WhereamigRPC(whereami_pb2_grpc.WhereamiServicer):
    def GetPayload(self, request, context):
        payload = whereami_payload.build_payload(None)
        return whereami_pb2.WhereamiReply(**payload)

def grpc_serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()+5),
        interceptors=(PromServerInterceptor(),))
    whereami_pb2_grpc.add_WhereamiServicer_to_server(WhereamigRPC(), server)
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=futures.ThreadPoolExecutor(max_workers=1))
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    services = tuple(
        service.full_name
        for service in whereami_pb2.DESCRIPTOR.services_by_name.values()) + (
            reflection.SERVICE_NAME, health.SERVICE_NAME)
    start_http_server(port=grpc_metrics_port)
    reflection.enable_server_reflection(services, server)
    server.add_insecure_port(host_ip + ':' + str(grpc_serving_port))
    server.start()
    overall_server_health = ""
    for service in services + (overall_server_health,):
        health_servicer.set(service, health_pb2.HealthCheckResponse.SERVING)
    server.wait_for_termination()

client = genai.Client(
    vertexai=True,
    project=os.environ["PROJECT_ID"],
    location="us-central1"
)

def _get_region(zone: str) -> str:
    elements = zone.split('-')
    return '-'.join(elements[:2])

def _get_location_from_json_list(file_path: str, region: str) -> str:
    with open(file_path, 'r') as file:
        data = json.load(file)
    for item in data['regions']:
        if item.get('name') == region:
            return item.get('location')
    return None

def stream_response(prompt):
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(prompt)]
        )
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=0.3,
        top_p=0.6,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ]
    )

    responses = client.models.generate_content_stream(
        model="gemini-2.0-flash-exp",
        contents=contents,
        config=generate_content_config
    )
    
    for response in responses:
        chunk = str(response).replace("•", "  *")
        chunk = markdown.markdown(chunk)
        yield f"data: {json.dumps({'chunk': chunk})}\n\n"

@app.route('/healthz')
@metrics.do_not_track()
def i_am_healthy():
    return ('OK')

@app.route('/api/', defaults={'path': ''})
@app.route('/api/<path:path>')
def api(path):
    payload = whereami_payload.build_payload(request.headers)
    requested_value = path.split('/')[-1]
    if requested_value in payload.keys():
        return payload[requested_value]
    return jsonify(payload)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == 'POST':
        prompt = request.form['prompt']
        return Response(stream_response(prompt), mimetype='text/event-stream')
        
    payload = whereami_payload.build_payload(request.headers)
    if 'region' in payload:
        region = payload['region']
    elif 'zone' in payload:
        region = _get_region(payload['zone'])
    else:
        logging.warning("Region cannot be located.")
        region = None

    location = _get_location_from_json_list('/app/regions.json', region)
    message = f"Hello from {region} in {location}!"
    prompt = f"What is an interesting fact about {location}?"
    return render_template('index.html', message=message, default_prompt=prompt)

if __name__ == '__main__':
    if os.getenv('GRPC_ENABLED') == "True":
        logging.info('gRPC server listening on port %s'%(grpc_serving_port))
        grpc_serve()
    else:
        app.run(
            host=host_ip.strip('[]'),
            port=int(os.environ.get('PORT', 8080)),
            debug=True,
            threaded=True)