# Maintenance

This document provides guidance on checking the health and status of the Dataset Profiler service.

## Health Checks

### Readiness Probe

A lightweight readiness probe that does **not** depend on Ray or Redis. This is the
endpoint Kubernetes should point its readiness/liveness probe at, so a transient
Ray or Redis outage never deregisters the pod from the Service:

```bash
# Check readiness
curl -X GET "https://{host}/monitoring/ready"
```

Expected response:
```json
{
  "status": "ready"
}
```

The root endpoint `GET /` is an equivalent pure-HTTP liveness target.

### Dependency Health Check

Monitor the health of the service and its dependencies (Redis and Ray). This
endpoint is purely diagnostic: it **always** returns HTTP 200 from a live pod and
reports a dependency being down inside the response body (`status: degraded`)
rather than as a non-200 status:

```bash
# Check dependency health
curl -X GET "https://{host}/monitoring/health-check"
```

Expected response:
```json
{
  "status": "healthy",
  "redis": {
    "status": "healthy",
    "message": "Connected to Redis server successfully."
  },
  "ray": {
    "status": "healthy",
    "message": "Ray cluster reachable with 3 alive node(s)."
  }
}
```

When a dependency is unavailable the overall `status` becomes `degraded` and the
affected dependency reports its own `status` and an explanatory `message`.

### Ray Cluster Health Check

Check the health of the Ray cluster:

```bash
# Check Ray cluster status
ray status
```
