import csv
import io
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app import schemas
from app.auth import get_current_user
from app.database import db

router = APIRouter(prefix='/api/reports', tags=['Reports'])


def _aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post('', response_model=schemas.ReportOut)
async def report(
    payload: schemas.ReportRequest,
    user: dict = Depends(get_current_user),
):
    if user.get('role') not in ('admin', 'employee'):
        raise HTTPException(status_code=403, detail='Staff only')

    start = _aware(payload.start_at)
    end = _aware(payload.end_at)
    match = {
        'start_at': {'$gte': start, '$lt': end},
    }
    if payload.resource_id:
        match['resource_id'] = payload.resource_id

    pipeline = [
        {'$match': match},
        {
            '$group': {
                '_id': '$resource_id',
                'total_bookings': {'$sum': 1},
                'confirmed_bookings': {
                    '$sum': {'$cond': [{'$eq': ['$status', 'confirmed']}, 1, 0]}
                },
                'completed_bookings': {
                    '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                },
                'cancelled_bookings': {
                    '$sum': {'$cond': [{'$eq': ['$status', 'cancelled']}, 1, 0]}
                },
                'total_minutes': {
                    '$sum': {
                        '$divide': [
                            {'$subtract': ['$end_at', '$start_at']},
                            60000,
                        ]
                    }
                },
            }
        },
    ]

    rows = []
    async for doc in db.bookings.aggregate(pipeline):
        resource = await db.resources.find_one({'_id': doc['_id']})
        rows.append(schemas.ReportRow(
            resource_id=doc['_id'],
            resource_name=resource['name'] if resource else doc['_id'],
            total_bookings=doc['total_bookings'],
            confirmed_bookings=doc['confirmed_bookings'],
            completed_bookings=doc['completed_bookings'],
            cancelled_bookings=doc['cancelled_bookings'],
            total_minutes=int(doc['total_minutes']),
        ))

    rows.sort(key=lambda r: r.resource_name)
    return schemas.ReportOut(rows=rows, period_start=start, period_end=end)


@router.post('/csv')
async def report_csv(
    payload: schemas.ReportRequest,
    user: dict = Depends(get_current_user),
):
    if user.get('role') not in ('admin', 'employee'):
        raise HTTPException(status_code=403, detail='Staff only')

    report = await _build_report(payload)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'resource_id', 'resource_name', 'total_bookings',
        'confirmed_bookings', 'completed_bookings', 'cancelled_bookings', 'total_minutes',
    ])
    for r in report.rows:
        writer.writerow([
            r.resource_id, r.resource_name, r.total_bookings,
            r.confirmed_bookings, r.completed_bookings, r.cancelled_bookings, r.total_minutes,
        ])

    buf.seek(0)
    filename = f"report_{payload.start_at.strftime('%Y%m%d')}_{payload.end_at.strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        buf,
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


async def _build_report(payload: schemas.ReportRequest) -> schemas.ReportOut:
    start = _aware(payload.start_at)
    end = _aware(payload.end_at)
    match = {'start_at': {'$gte': start, '$lt': end}}
    if payload.resource_id:
        match['resource_id'] = payload.resource_id

    pipeline = [
        {'$match': match},
        {
            '$group': {
                '_id': '$resource_id',
                'total_bookings': {'$sum': 1},
                'confirmed_bookings': {
                    '$sum': {'$cond': [{'$eq': ['$status', 'confirmed']}, 1, 0]}
                },
                'completed_bookings': {
                    '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                },
                'cancelled_bookings': {
                    '$sum': {'$cond': [{'$eq': ['$status', 'cancelled']}, 1, 0]}
                },
                'total_minutes': {
                    '$sum': {
                        '$divide': [
                            {'$subtract': ['$end_at', '$start_at']},
                            60000,
                        ]
                    }
                },
            }
        },
    ]

    rows = []
    async for doc in db.bookings.aggregate(pipeline):
        resource = await db.resources.find_one({'_id': doc['_id']})
        rows.append(schemas.ReportRow(
            resource_id=doc['_id'],
            resource_name=resource['name'] if resource else doc['_id'],
            total_bookings=doc['total_bookings'],
            confirmed_bookings=doc['confirmed_bookings'],
            completed_bookings=doc['completed_bookings'],
            cancelled_bookings=doc['cancelled_bookings'],
            total_minutes=int(doc['total_minutes']),
        ))

    rows.sort(key=lambda r: r.resource_name)
    return schemas.ReportOut(rows=rows, period_start=start, period_end=end)