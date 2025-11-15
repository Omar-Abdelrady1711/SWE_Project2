from fastapi import APIRouter, HTTPException, Header, Depends
from sqlalchemy.orm import Session

from bs.src.database import get_db   
from bs.src.db_models import ArtifactModel  

from acemcli.orchestrator import compute_for_single
from acemcli.models import MetricResult

from bs.src.schemas import ModelRating  # the schema we will create


router = APIRouter()


@router.get(
    "/artifact/model/{id}/rate",
    response_model=ModelRating,
    summary="Compute and return rating metrics for a model artifact (BASELINE)"
)
def rate_model(
    id: int,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_db),
):
    """
    Implements the Phase 2 Model Rating endpoint.
    """

    # 1 — Find artifact
    artifact = db.query(ArtifactModel).filter(ArtifactModel.id == id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # 2 — Artifact must be a model
    if artifact.type.lower() != "model":
        raise HTTPException(status_code=400, detail="Artifact is not a model")

    # 3 — Extract model URL
    url = getattr(artifact, "url", None) or artifact.description
    if not url:
        raise HTTPException(status_code=400, detail="Model has no URL to compute metrics")

    # 4 — Compute metrics
    try:
        res: MetricResult = compute_for_single(url, "MODEL")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metric computation failed: {str(e)}")

    # 5 — Convert MetricResult → Pydantic ModelRating
    return ModelRating(
        name=res.name,
        category=res.category,

        net_score=res.net_score,
        net_score_latency=res.net_score_latency,

        ramp_up_time=res.ramp_up_time,
        ramp_up_time_latency=res.ramp_up_time_latency,

        bus_factor=res.bus_factor,
        bus_factor_latency=res.bus_factor_latency,

        performance_claims=res.performance_claims,
        performance_claims_latency=res.performance_claims_latency,

        license=res.license,
        license_latency=res.license_latency,

        dataset_and_code_score=res.dataset_and_code_score,
        dataset_and_code_score_latency=res.dataset_and_code_score_latency,

        dataset_quality=res.dataset_quality,
        dataset_quality_latency=res.dataset_quality_latency,

        code_quality=res.code_quality,
        code_quality_latency=res.code_quality_latency,

        tree_score=res.tree_score,
        tree_score_latency=res.tree_score_latency,

        reproducibility=res.reproducibility,
        reproducibility_latency=res.reproducibility_latency,

        reviewedness=res.reviewedness,
        reviewedness_latency=res.reviewedness_latency,

        size_score=res.size_score,
        size_score_latency=res.size_score_latency,
    )
