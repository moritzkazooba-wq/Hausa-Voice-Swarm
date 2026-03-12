# Kubernetes Manifests

## Per-Component Manifests
- Deployment, Service, HPA for each component (voice, api, agents)
- ConfigMaps for non-sensitive configuration
- Secrets managed externally (not committed)

## HPA
- Custom metric: `active_voice_sessions` via prometheus-adapter
- Scale voice-agent pods based on active session count
- Min replicas: 2, Max replicas: 20

## Reliability
- `terminationGracePeriodSeconds: 300` — allow active calls to complete
- PodDisruptionBudget: `minAvailable: 1` per component
- NetworkPolicy: restrict inter-pod traffic to required paths only

## prometheus-adapter
- Custom metrics API configuration
- Maps Prometheus `active_sessions` gauge to k8s custom metrics API
