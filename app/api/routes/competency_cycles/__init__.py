"""Competency-cycle API routes (self/manager assessment, radar data, IDP).

Replaces the previous 834-line app/api/routes/competency_cycles.py.
Split by concern; this file re-aggregates the sub-routers so the public
import (`from app.api.routes.competency_cycles import router`) is unchanged.
"""
from fastapi import APIRouter

from .cycle import router as cycle_router
from .assessments import router as assessments_router
from .radar import router as radar_router
from .development_plan import router as development_plan_router

<<<<<<< HEAD
<<<<<<< HEAD
router = APIRouter()
=======
router = APIRouter(tags=["Employees"])
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
router = APIRouter()
>>>>>>> 2abb2b4 (fixing issues with swagger and adding more test to performance testing)

router.include_router(cycle_router)
router.include_router(assessments_router)
router.include_router(radar_router)
router.include_router(development_plan_router)
