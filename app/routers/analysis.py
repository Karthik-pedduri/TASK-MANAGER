from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.services.analysis import (
    completion_stats,
    overdue_stats,
    generate_priority_pie,
    generate_completion_trends,
    generate_csv_report,
    stage_variance_stats,
    generate_delay_bar,
    generate_scatter_plot,
    generate_tasks_per_day,
    get_task_dataframe,
    get_stage_dataframe,
    generate_bottleneck_chart,
    generate_productivity_heatmap
)
import io

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.get("/completion")
async def get_completion_stats(db: AsyncSession = Depends(get_db)):
    return await completion_stats(db)

@router.get("/overdue")
async def get_overdue_stats(db: AsyncSession = Depends(get_db)):
    return await overdue_stats(db)

@router.get("/visualizations/priority")
async def get_priority_chart(db: AsyncSession = Depends(get_db)):
    df = await get_task_dataframe(db)
    img_buf = await run_in_threadpool(generate_priority_pie, df)
    if not img_buf:
        return {"message": "No data"}
    return StreamingResponse(img_buf, media_type="image/png")

@router.get("/visualizations/completion-trends")
async def get_completion_trends(db: AsyncSession = Depends(get_db)):
    df = await get_task_dataframe(db)
    img_buf = await run_in_threadpool(generate_completion_trends, df)
    if not img_buf:
        return {"message": "No data"}
    return StreamingResponse(img_buf, media_type="image/png")

@router.get("/reports/csv")
async def get_csv_report(db: AsyncSession = Depends(get_db)):
    csv_data = await generate_csv_report(db)
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks_report.csv"}
    )

@router.get("/stage-variance")
async def get_stage_variance(db: AsyncSession = Depends(get_db)):
    return await stage_variance_stats(db)

@router.get("/visualizations/delay")
async def get_delay_chart(db: AsyncSession = Depends(get_db)):
    df = await get_task_dataframe(db)
    img_buf = await run_in_threadpool(generate_delay_bar, df)
    if not img_buf:
        return {"message": "No data"}
    return StreamingResponse(img_buf, media_type="image/png")

@router.get("/visualizations/scatter-duration")
async def get_scatter_plot_endpoint(db: AsyncSession = Depends(get_db)):
    df = await get_task_dataframe(db)
    img_buf = await run_in_threadpool(generate_scatter_plot, df)
    if not img_buf:
        return {"message": "No data"}
    return StreamingResponse(img_buf, media_type="image/png")

@router.get("/visualizations/daily-tasks")
async def get_daily_tasks_chart(db: AsyncSession = Depends(get_db)):
    df = await get_task_dataframe(db)
    img_buf = await run_in_threadpool(generate_tasks_per_day, df)
    if not img_buf:
        return {"message": "No data"}
    return StreamingResponse(img_buf, media_type="image/png")

@router.get("/visualizations/bottlenecks")
async def get_bottlenecks_chart(db: AsyncSession = Depends(get_db)):
    df = await get_stage_dataframe(db)
    img_buf = await run_in_threadpool(generate_bottleneck_chart, df)
    if not img_buf:
        return {"message": "No data"}
    return StreamingResponse(img_buf, media_type="image/png")

@router.get("/visualizations/heatmap")
async def get_heatmap_chart(db: AsyncSession = Depends(get_db)):
    df = await get_task_dataframe(db)
    img_buf = await run_in_threadpool(generate_productivity_heatmap, df)
    if not img_buf:
        return {"message": "No data"}
    return StreamingResponse(img_buf, media_type="image/png")