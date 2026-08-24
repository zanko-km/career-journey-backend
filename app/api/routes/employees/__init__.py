"""Employee-scoped API routes.

This package replaces the previous 2500+ line app/api/routes/employees.py.
Each module owns one slice of the /employees/{employee_id}/... surface;
this file aggregates them under the single /employees prefix so the public
import (`from app.api.routes.employees import router`) is unchanged.
"""
from fastapi import APIRouter

from .crud import router as crud_router
from .onboarding import router as onboarding_router
from .onboarding_phases import router as onboarding_phases_router
from .onboarding_actions import router as onboarding_actions_router
from .onboarding_feedback import router as onboarding_feedback_router
from .decisions import router as decisions_router
from .competencies import router as competencies_router
from .roles import router as roles_router

<<<<<<< HEAD
<<<<<<< HEAD
router = APIRouter()
=======
router = APIRouter(tags=["Employees"])
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
router = APIRouter()
>>>>>>> 2abb2b4 (fixing issues with swagger and adding more test to performance testing)

router.include_router(crud_router)
router.include_router(onboarding_router)
router.include_router(onboarding_phases_router)
router.include_router(onboarding_actions_router)
router.include_router(onboarding_feedback_router)
router.include_router(decisions_router)
router.include_router(competencies_router)
router.include_router(roles_router)
