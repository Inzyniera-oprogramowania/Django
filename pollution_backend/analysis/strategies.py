from dataclasses import asdict
from typing import Any, Tuple
from rest_framework.serializers import Serializer

from pollution_backend.services.statistics import (
    get_descriptive_stats,
    get_trend_analysis,
    get_period_comparison,
    get_norm_exceedance_analysis,
)
from pollution_backend.analysis.api.serializers import (
    DescriptiveStatsSerializer,
    TrendAnalysisSerializer,
    PeriodComparisonSerializer,
    NormExceedanceSerializer,
)

class AnalysisStrategy:
    @staticmethod
    def run(analysis_type: str, data: dict) -> Tuple[Any, Serializer]:
        sensor_id = data["sensor_id"]
        date_from = data["date_from"]
        date_to = data["date_to"]

        if analysis_type == "descriptive":
            result = get_descriptive_stats(sensor_id, date_from, date_to)
            return result, DescriptiveStatsSerializer

        elif analysis_type == "trend":
            aggregation = data.get("aggregation", "hour")
            result = get_trend_analysis(sensor_id, date_from, date_to, aggregation)
            return result, TrendAnalysisSerializer

        elif analysis_type == "comparison":
            result = get_period_comparison(
                sensor_id, date_from, date_to, 
                data["period2_from"], data["period2_to"]
            )
            return result, PeriodComparisonSerializer

        elif analysis_type == "exceedance":
            result = get_norm_exceedance_analysis(sensor_id, date_from, date_to)
            return result, NormExceedanceSerializer
        
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

    @staticmethod
    def serialize_result(result: Any, serializer_cls: Serializer) -> dict:
        if result is None:
            return None
        return serializer_cls(asdict(result)).data