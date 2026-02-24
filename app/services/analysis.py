import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from matplotlib.figure import Figure

import io
import seaborn as sns
import base64
from sqlalchemy.orm import Session, aliased
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case, Subquery, desc, and_, DateTime
from app.models.tasks import Task as TaskModel, TaskStage as TaskStageModel, State
from datetime import date, datetime

async def get_task_dataframe(db: AsyncSession) -> pd.DataFrame:
    result = await db.execute(select(State))
    states = result.scalars().all()
    state_map = {s.state_id: s.state_name for s in states}

    result = await db.execute(
        select(
            TaskModel.task_id, TaskModel.name, TaskModel.priority, 
            TaskModel.status_state_id, TaskModel.created_at, 
            TaskModel.due_date, TaskModel.completed_date
        ).filter(TaskModel.is_deleted == False)
    )
    rows = result.all()
    
    if not rows:
        return pd.DataFrame(columns=[
            "task_id", "name", "priority", "status", "created_at", 
            "due_date", "completed_date", "duration_days", "delay_days"
        ])
    
    # SA 1.4/2.0+ rows are tuple-like, can convert to dict/list
    data = []
    for row in rows:
        # accessing by index or attribute if they are Row objects
        data.append({
            "task_id": row.task_id,
            "name": row.name,
            "priority": row.priority,
            "status_state_id": row.status_state_id,
            "created_at": row.created_at,
            "due_date": row.due_date,
            "completed_date": row.completed_date
        })

    df = pd.DataFrame(data)

    df["status"] = df["status_state_id"].map(state_map)

    df["due_date"] = pd.to_datetime(df["due_date"], utc=True).dt.normalize()
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.normalize()
    
    if "completed_date" in df.columns:
         df["completed_date"] = pd.to_datetime(df["completed_date"], utc=True).dt.normalize()

    df["duration_days"] = (df["completed_date"] - df["created_at"]).dt.days
    df["delay_days"] = (df["completed_date"] - df["due_date"]).dt.days

    return df


async def get_stage_dataframe(db: AsyncSession) -> pd.DataFrame:
    result = await db.execute(select(State))
    states = result.scalars().all()
    state_map = {s.state_id: s.state_name for s in states}

    result = await db.execute(
        select(
            TaskStageModel.stage_id, TaskStageModel.task_id, 
            TaskStageModel.stage_name, TaskStageModel.estimated_time_hours, 
            TaskStageModel.actual_time_hours, TaskStageModel.status_state_id
        ).join(TaskModel).filter(TaskModel.is_deleted == False)
    )
    rows = result.all()
    
    if not rows:
         return pd.DataFrame(columns=[
            "stage_id", "task_id", "stage_name", "estimated_hours", 
            "actual_hours", "variance_hours", "status"
        ])
    
    data = []
    for row in rows:
        data.append({
            "stage_id": row.stage_id,
            "task_id": row.task_id,
            "stage_name": row.stage_name,
            "estimated_time_hours": row.estimated_time_hours,
            "actual_time_hours": row.actual_time_hours,
            "status_state_id": row.status_state_id
        })

    df = pd.DataFrame(data)

    df["status"] = df["status_state_id"].map(state_map)
    df["variance_hours"] = df["actual_time_hours"] - df["estimated_time_hours"].fillna(0)
    
    return df

async def completion_stats(db: AsyncSession) -> dict:
    state_alias = aliased(State)

    result = await db.execute(select(State.state_id).filter(State.state_name == "completed"))
    completed_state_id = result.scalars().first()
    
    if not completed_state_id:
        return {"message": "completion state not found"}

    # Total completed
    total_completed_query = select(func.count(TaskModel.task_id)).filter(
        TaskModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    )
    total_completed = (await db.execute(total_completed_query)).scalar()

    if total_completed == 0:
        return {"message": "no completed tasks yet"}

    # Date differences (handling both PostgreSQL style and generic style roughly - simplistic approach for varied dialects)
    # Generic approach: extract days between completed_date and created_at
    # PostgreSQL specific: func.extract('epoch', TaskModel.completed_date - TaskModel.created_at) / 86400
    
    # We will compute the average duration dynamically across all completed tasks.
    # To keep it dialect agnostic for now, we use a more raw SQL computation or fetch the minimal fields
    
    # A cleaner approach for database-agnostic avg duration is to fetch the relevant fields 
    # and compute in Python, OR assume PostgreSQL since we use asyncpg:
    duration_expr = func.extract('epoch', func.cast(TaskModel.completed_date, DateTime) - TaskModel.created_at) / 86400.0
    delay_expr = func.extract('epoch', func.cast(TaskModel.completed_date, DateTime) - func.cast(TaskModel.due_date, DateTime)) / 86400.0

    stats_query = select(
        func.avg(duration_expr).label("avg_duration"),
        func.avg(delay_expr).label("avg_delay")
    ).filter(
        TaskModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    )
    
    stats_result = (await db.execute(stats_query)).first()
    avg_duration_days = float(stats_result.avg_duration or 0.0)
    avg_delay_days = float(stats_result.avg_delay or 0.0)

    # On-time percentage
    on_time_query = select(func.count(TaskModel.task_id)).filter(
        TaskModel.status_state_id == completed_state_id,
        TaskModel.completed_date <= TaskModel.due_date,
        TaskModel.is_deleted == False
    )
    on_time_count = (await db.execute(on_time_query)).scalar()
    on_time_percentage = (on_time_count / total_completed) * 100.0

    # Group by priority
    priority_query = select(
        TaskModel.priority,
        func.count(TaskModel.task_id).label("count"),
        func.avg(duration_expr).label("avg_duration"),
        func.avg(delay_expr).label("avg_delay")
    ).filter(
        TaskModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    ).group_by(TaskModel.priority)
    
    priority_results = (await db.execute(priority_query)).all()
    
    by_priority = {}
    for pr in priority_results:
        by_priority[pr.priority] = {
            "count": pr.count,
            "duration_days": float(pr.avg_duration or 0.0),
            "delay_days": float(pr.avg_delay or 0.0)
        }

    return {
        "total_completed": total_completed,
        "avg_duration_days": avg_duration_days,
        "avg_delay_days": avg_delay_days,
        "on_time_percentage": on_time_percentage,
        "by_priority": by_priority
    }

async def stage_variance_stats(db: AsyncSession) -> dict:
    state_alias = aliased(State)

    completed_state_query = select(State.state_id).filter(State.state_name == "completed")
    completed_state_id = (await db.execute(completed_state_query)).scalars().first()
    
    if not completed_state_id:
        return {"message": "completion state not found"}

    base_query = select(TaskStageModel).join(TaskModel).filter(
        TaskStageModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    )
    
    total_completed_stages_q = select(func.count(TaskStageModel.stage_id)).join(TaskModel).filter(
        TaskStageModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    )
    total_completed_stages = (await db.execute(total_completed_stages_q)).scalar()
    
    if total_completed_stages == 0:
        return {"message": "no completed stages yet"}

    variance_expr = TaskStageModel.actual_time_hours - func.coalesce(TaskStageModel.estimated_time_hours, 0.0)

    avg_variance_q = select(func.avg(variance_expr)).join(TaskModel).filter(
        TaskStageModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    )
    avg_variance_hours = float((await db.execute(avg_variance_q)).scalar() or 0.0)

    most_over_q = select(TaskStageModel.stage_name, variance_expr.label('variance_hours')).join(TaskModel).filter(
        TaskStageModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    ).order_by(variance_expr.asc()).limit(5)
    
    most_over = [{"stage_name": row.stage_name, "variance_hours": float(row.variance_hours or 0.0)} for row in (await db.execute(most_over_q)).all()]

    most_under_q = select(TaskStageModel.stage_name, variance_expr.label('variance_hours')).join(TaskModel).filter(
        TaskStageModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    ).order_by(variance_expr.desc()).limit(5)
    
    most_under = [{"stage_name": row.stage_name, "variance_hours": float(row.variance_hours or 0.0)} for row in (await db.execute(most_under_q)).all()]

    by_stage_q = select(
        TaskStageModel.stage_name,
        func.avg(variance_expr).label('mean_variance_hours'),
        func.count(TaskStageModel.stage_id).label('count')
    ).join(TaskModel).filter(
        TaskStageModel.status_state_id == completed_state_id,
        TaskModel.is_deleted == False
    ).group_by(TaskStageModel.stage_name)

    by_stage_results = (await db.execute(by_stage_q)).all()
    by_stage_name = {
        row.stage_name: {
            "mean_variance_hours": float(row.mean_variance_hours or 0.0),
            "count": row.count
        } for row in by_stage_results
    }

    return {
        "total_completed_stages": total_completed_stages,
        "avg_variance_hours": avg_variance_hours,
        "most_overestimated_stages": most_over,
        "most_underestimated_stages": most_under,
        "by_stage_name": by_stage_name
    }


async def overdue_stats(db: AsyncSession) -> dict:
    states_q = await db.execute(select(State))
    states = states_q.scalars().all()
    state_map = {s.state_name: s.state_id for s in states}
    
    completed_id = state_map.get("completed")
    overdue_id = state_map.get("overdue")

    today_date = date.today()

    total_q = select(func.count(TaskModel.task_id)).filter(TaskModel.is_deleted == False)
    total_tasks = (await db.execute(total_q)).scalar()

    overdue_q = select(func.count(TaskModel.task_id)).filter(
        and_(
            TaskModel.is_deleted == False,
            case(
                (TaskModel.status_state_id == overdue_id, True),
                ((TaskModel.status_state_id != completed_id) & (TaskModel.due_date < today_date), True),
                else_=False
            ) == True
        )
    )
    overdue_count = (await db.execute(overdue_q)).scalar()

    return {
        "overdue_count": overdue_count,
        "overdue_percentage": round(overdue_count / total_tasks * 100, 2) if total_tasks > 0 else 0,
        "total_tasks": total_tasks
    }
    
def generate_priority_pie(df: pd.DataFrame) -> str:
    counts = df["priority"].value_counts()
    if counts.empty:
        return ""
    
    # Thread-safe plotting using OO API
    fig = Figure(figsize=(6, 6))
    ax = fig.subplots()
    ax.pie(counts, labels=counts.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Task Distribution by priority")
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf

def generate_completion_trends(df: pd.DataFrame) -> str:
    completed = df[df["status"] == "completed"].copy()
    if completed.empty:
        return ""
    completed["completed_month"] = pd.to_datetime(completed["completed_date"]).dt.to_period("M").astype(str)
    trends = completed.groupby("completed_month").size().reset_index(name="completions")
    
    fig = Figure(figsize=(10, 5))
    ax = fig.subplots()
    sns.barplot(data=trends, x="completed_month", y="completions", palette="viridis", ax=ax)
    ax.set_title("Task Completions Over Time (Monthly)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Completed Tasks")
    ax.tick_params(axis='x', rotation=45)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

def generate_delay_bar(df: pd.DataFrame) -> str:
    completed = df[df["status"] == "completed"]

    if completed.empty:
        return ""
    avg_delay = completed.groupby("priority")["delay_days"].mean().reset_index()
    
    fig = Figure(figsize=(8, 5))
    ax = fig.subplots()
    sns.barplot(data=avg_delay, x="priority", y="delay_days", palette="coolwarm", ax=ax)
    ax.set_title("Average Delay by Priority (Days)")
    ax.set_ylabel("Avg Delay (Positive = Late)")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf

def generate_scatter_plot(df: pd.DataFrame) -> str:
    completed = df[df["status"] == "completed"]

    if completed.empty or "duration_days" not in completed.columns:
        return ""

    fig = Figure(figsize=(10, 6))
    ax = fig.subplots()
    
    # Map priority to numbers for plotting if needed, or use hue
    sns.scatterplot(
        data=completed, 
        x="priority", 
        y="duration_days", 
        hue="priority", 
        s=100, 
        palette="deep",
        ax=ax
    )
    ax.set_title("Time to Complete vs Task Priority")
    ax.set_ylabel("Duration (Days)")
    ax.grid(True, linestyle="--", alpha=0.7)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf

def generate_tasks_per_day(df: pd.DataFrame) -> str:
    completed = df[df["status"] == "completed"].copy()
    
    if completed.empty:
        return ""
        
    # Count per day
    # Ensure we group by date string to avoid timezone/time display issues
    completed["date_str"] = completed["completed_date"].dt.date.astype(str)
    daily_counts = completed.groupby("date_str").size().reset_index(name="count")
    
    fig = Figure(figsize=(10, 5))
    ax = fig.subplots()
    sns.barplot(data=daily_counts, x="date_str", y="count", color="skyblue", ax=ax)
    ax.set_title("Tasks Completed Per Day")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Tasks")
    ax.tick_params(axis='x', rotation=45)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

async def generate_csv_report(db: AsyncSession) -> str:
    task_df = await get_task_dataframe(db)
    stage_df = await get_stage_dataframe(db)
    merged = task_df.merge(stage_df, on="task_id", how="left", suffixes=("_task", "_stage"))
    return merged.to_csv(index=False)

def generate_bottleneck_chart(df: pd.DataFrame) -> io.BytesIO:
    if df.empty or "variance_hours" not in df.columns:
        return None
    
    # Identify stages with high variance
    bottlenecks = df.groupby("stage_name")["variance_hours"].mean().sort_values(ascending=False).head(10).reset_index()
    
    fig = Figure(figsize=(10, 6))
    ax = fig.subplots()
    sns.barplot(data=bottlenecks, x="variance_hours", y="stage_name", palette="Reds_r", ax=ax)
    ax.set_title("Top 10 Bottleneck Stages (Avg Variance Hours)")
    ax.set_xlabel("Mean Variance (Actual - Estimated)")
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

def generate_productivity_heatmap(df: pd.DataFrame) -> io.BytesIO:
    completed = df[df["status"] == "completed"].copy()
    if completed.empty:
        return None
    
    completed["weekday"] = completed["completed_date"].dt.day_name()
    completed["week"] = completed["completed_date"].dt.isocalendar().week
    
    # Simple pivot for heatmap: Week vs Weekday
    heatmap_data = completed.groupby(["week", "weekday"]).size().unstack(fill_value=0)
    
    # Reorder weekdays
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_data = heatmap_data.reindex(columns=[d for d in days if d in heatmap_data.columns])
    
    fig = Figure(figsize=(12, 6))
    ax = fig.subplots()
    sns.heatmap(heatmap_data, annot=True, fmt="d", cmap="YlGnBu", ax=ax)
    ax.set_title("Productivity Heatmap (Tasks Completed per Week/Day)")
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf