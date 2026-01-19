"""Early access signup API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from sqlalchemy.exc import IntegrityError

from optifiner_api.models import EarlyAccessSignupRequest, EarlyAccessSignupResponse
from optifiner_api.database import get_db_context
from optifiner_api import crud

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/early-access/signup", response_model=EarlyAccessSignupResponse)
async def create_early_access_signup(
    request_data: EarlyAccessSignupRequest,
    request: Request,
):
    """Create a new early access signup."""
    try:
        user_agent = request.headers.get("user-agent")
        ip_address = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
        if ip_address and "," in ip_address:
            ip_address = ip_address.split(",")[0].strip()

        async with get_db_context() as db:
            existing = await crud.get_early_access_signup_by_email(db, request_data.email)

            if existing:
                logger.info(f"Duplicate signup attempt for: {request_data.email}")
                return EarlyAccessSignupResponse(
                    success=True,
                    message="Thanks for your interest! We'll notify you when we're ready.",
                    email=request_data.email,
                    already_registered=True,
                )

            signup = await crud.create_early_access_signup(
                db=db,
                email=request_data.email,
                source=request_data.source,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            logger.info(f"New early access signup: {signup.email} from {request_data.source}")

            return EarlyAccessSignupResponse(
                success=True,
                message="Thanks for signing up! We'll notify you when Optifiner is ready.",
                email=signup.email,
                already_registered=False,
            )

    except IntegrityError:
        logger.warning(f"Race condition on signup for: {request_data.email}")
        return EarlyAccessSignupResponse(
            success=True,
            message="Thanks for your interest! We'll notify you when we're ready.",
            email=request_data.email,
            already_registered=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating early access signup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred processing your signup")


@router.get("/early-access/signups")
async def list_early_access_signups(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all early access signups (admin endpoint)."""
    try:
        async with get_db_context() as db:
            signups = await crud.get_early_access_signups(db=db, status=status, skip=skip, limit=limit)
            total = await crud.count_early_access_signups(db=db, status=status)

            return {
                "signups": [s.to_dict() for s in signups],
                "total": total,
                "skip": skip,
                "limit": limit,
            }
    except Exception as e:
        logger.error(f"Error listing signups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/early-access/stats")
async def get_early_access_stats():
    """Get early access signup statistics."""
    try:
        async with get_db_context() as db:
            total = await crud.count_early_access_signups(db=db)
            pending = await crud.count_early_access_signups(db=db, status="pending")
            notified = await crud.count_early_access_signups(db=db, status="notified")

            return {
                "total": total,
                "pending": pending,
                "notified": notified,
            }
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
