"""
Orizon Zero Trust Connect - Metrics API Endpoint
For: Marco @ Syneto/Orizon

Prometheus metrics export
"""

from fastapi import APIRouter, Response
from loguru import logger

from app.monitoring.metrics import get_metrics

router = APIRouter()


@router.get("")
async def prometheus_metrics():
    """
    Export Prometheus metrics

    Returns metrics in Prometheus text exposition format
    No authentication required (typically scraped by Prometheus)
    """
    try:
        metrics_data, content_type = get_metrics()

        return Response(
            content=metrics_data,
            media_type=content_type
        )

    except Exception as e:
        logger.error(f"❌ Error exporting metrics: {e}")
        return Response(
            content=f"# Error exporting metrics: {str(e)}",
            media_type="text/plain",
            status_code=500
        )
