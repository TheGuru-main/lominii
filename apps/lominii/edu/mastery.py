from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.database import get_db
from platform.auth import get_current_user
from platform.models import ConceptMastery, Concept
from platform.schemas import MasteryOut

router = APIRouter()


@router.get(
    "",
    response_model=list[MasteryOut],
    summary="Student mastery"
)
async def get_mastery(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns mastery percentages for all concepts
    studied by the current student.
    """

    result = await db.execute(
        select(
            ConceptMastery,
            Concept.name
        )
        .join(
            Concept,
            Concept.id == ConceptMastery.concept_id
        )
        .where(
            ConceptMastery.student_id == current_user.id
        )
        .order_by(
            ConceptMastery.mastery.desc()
        )
    )

    rows = result.all()

    return [
        MasteryOut(
            concept_id=row.ConceptMastery.concept_id,
            concept_name=row.name,
            mastery=row.ConceptMastery.mastery,
        )
        for row in rows
    ]