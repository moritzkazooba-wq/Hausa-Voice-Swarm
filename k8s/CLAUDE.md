# Kubernetes Manifests

## Namespace
- `namespace.yaml` — `hausa-voice-swarm` namespace

## Deployments
- `voice-pipeline-deployment.yaml` — 2 min replicas, 2CPU/4Gi requests, GPU toleration, terminationGracePeriod 300s, preStop sleep 5
- `agent-api-deployment.yaml` — 2 min replicas, 1CPU/2Gi requests, terminationGracePeriod 30s

## Services
- `voice-pipeline-service.yaml` — LoadBalancer, ports 8000 + 8765
- `agent-api-service.yaml` — ClusterIP, port 8000

## HPA (Custom Metric)
- `hpa.yaml` — scales voice-pipeline on `hsv_active_voice_sessions` (AverageValue 5), min 2 / max 50
- Scale-up: stabilization 30s, +5 pods per 30s
- Scale-down: stabilization 300s, -10% per 60s

## prometheus-adapter
- `prometheus-adapter-configmap.yaml` — maps `hsv_active_voice_sessions` gauge to custom metrics API
- `prometheus-adapter-deployment.yaml` — v0.11.2, connects to Prometheus at `prometheus.hausa-voice-swarm.svc:9090`
- `prometheus-adapter-service.yaml` — ClusterIP on 443→6443
- `prometheus-adapter-apiservice.yaml` — registers `v1beta1.custom.metrics.k8s.io`

## Configuration
- `configmap.yaml` — non-sensitive env vars (REDIS_URL, KAFKA_BOOTSTRAP_SERVERS, etc.)
- `secrets.yaml` — template with placeholder values (replace before applying)

## Reliability
- `pdb.yaml` — PodDisruptionBudget `minAvailable: 1` for both deployments
- `network-policy.yaml` — voice↔api ingress/egress, api→db/redis/kafka egress
- `service-monitor.yaml` — Prometheus Operator ServiceMonitor, scrapes `/metrics` every 15s

## Apply Order
```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml -f secrets.yaml
kubectl apply -f voice-pipeline-deployment.yaml -f voice-pipeline-service.yaml
kubectl apply -f agent-api-deployment.yaml -f agent-api-service.yaml
kubectl apply -f pdb.yaml -f network-policy.yaml -f service-monitor.yaml
kubectl apply -f prometheus-adapter-configmap.yaml -f prometheus-adapter-deployment.yaml
kubectl apply -f prometheus-adapter-service.yaml -f prometheus-adapter-apiservice.yaml
kubectl apply -f hpa.yaml
```
