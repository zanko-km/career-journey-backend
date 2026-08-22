"""Meeting API routes.

Replaces the previous 634-line app/api/routes/meetings.py. Split into
read endpoints (queries.py) and write/action endpoints (actions.py);
this file re-aggregates them so the public import
(`from app.api.routes.meetings import router`) is unchanged.
"""
from fastapi import APIRouter

from .queries import router as queries_router
from .actions import router as actions_router

<<<<<<< HEAD
router = APIRouter()
=======
router = APIRouter(tags=["Employees"])
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)

router.include_router(queries_router)
router.include_router(actions_router)
