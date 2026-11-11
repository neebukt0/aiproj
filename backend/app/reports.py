import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app import schemas
from app.auth import get_current_user
from app.database import db
from app.utils import as_utc

router = APIRouter(prefix='/api/reports', tags=['Reports'])


def _validate_period(payload: schemas.ReportRequest) -> tuple:
    start = as_utc(payload.start_at)
    end = as_utc(payload.end_at)
    if end <= start:
        raise HTTPException(status_code=400, detail='end_at must be after start_at')
    return start, end


async def _build_report(payload: schemas.ReportRequest) -> schemas.ReportOut:
    start, end = _validate_period(payload)
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


@router.post('', response_model=schemas.ReportOut)
async def report(
    payload: schemas.ReportRequest,
    user: dict = Depends(get_current_user),
):
    if user.get('role') not in ('admin', 'employee'):
        raise HTTPException(status_code=403, detail='Staff only')
    return await _build_report(payload)


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
    for row in report.rows:
        writer.writerow([
            row.resource_id, row.resource_name, row.total_bookings,
            row.confirmed_bookings, row.completed_bookings,
            row.cancelled_bookings, row.total_minutes,
        ])

    buf.seek(0)
    start, end = _validate_period(payload)
    filename = f"report_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        buf,
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
