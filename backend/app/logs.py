from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app import schemas
from app.auth import get_current_user
from app.database import db
from app.utils import as_utc

router = APIRouter(prefix='/api/logs', tags=['Logs'])

status_logs_col = db.status_logs


@router.get('', response_model=List[schemas.StatusLogOut])
async def list_logs(
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    if user.get('role') not in ('admin', 'employee'):
        raise HTTPException(status_code=403, detail='Staff only')

    cursor = status_logs_col.find({}).sort('changed_at', -1).limit(limit)
    out = []
    async for doc in cursor:
        out.append(schemas.StatusLogOut(
            id=str(doc['_id']),
            booking_id=doc['booking_id'],
            from_status=doc.get('from_status'),
            to_status=doc['to_status'],
            changed_by=doc.get('changed_by'),
            changed_at=as_utc(doc['changed_at']),
            note=doc.get('note'),
        ))
    return out
