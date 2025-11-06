# Maintenance

This document provides guidance on checking the health and status of the Dataset Profiler service.

## Health Checks

### API Health Check

Monitor the API health endpoint:

```bash
# Check API health
curl -X GET "https://{host}/health"
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.0.1",
  "dependencies": {
    "ray": {
      "status": "healthy",
      "message": "Ray cluster reachable with 3 alive node(s)."
    },
    "storage": {
      "status": "healthy",
      "message": "Storage accessible"
    }
  }
}
```

### Ray Cluster Health Check

Check the health of the Ray cluster:

```bash
# Check Ray cluster status
ray status
```
