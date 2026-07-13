"""
LOMINII EDU Router

Main router for the EDU workspace.
All EDU modules are registered here.
"""

from fastapi import APIRouter

from . import (
    onboarding,
    dashboard,
    curriculum,
    classroom,
    practice,
    exams,
    mastery,
    analytics,
    ai,
    institutions,
    notifications,
    library,
    bookshop,
    settings,
    profile,
)

router = APIRouter(
    prefix="/api/edu",
    tags=["LOMINII EDU"],
)

# ==========================================================
# EDU MODULES
# ==========================================================

router.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])

router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

router.include_router(curriculum.router, prefix="/curriculum", tags=["Curriculum"])

router.include_router(classroom.router, prefix="/classroom", tags=["Classroom"])

router.include_router(practice.router, prefix="/practice", tags=["Practice"])

router.include_router(exams.router, prefix="/exams", tags=["Exams"])

router.include_router(mastery.router, prefix="/mastery", tags=["Mastery"])

router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

router.include_router(ai.router, prefix="/ai", tags=["AI Tutor"])

router.include_router(institutions.router, prefix="/institutions", tags=["Institutions"])

router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

router.include_router(library.router, prefix="/library", tags=["Library"])

router.include_router(bookshop.router, prefix="/bookshop", tags=["Bookshop"])

router.include_router(settings.router, prefix="/settings", tags=["Settings"])

router.include_router(profile.router, prefix="/profile", tags=["Profile"])