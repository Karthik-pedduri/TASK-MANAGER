"""
Realistic Mock Data Generation Script for Task Manager
Generates realistic users, tasks, and stages with actual names and business-realistic scenarios
"""
import sys
import os
from datetime import datetime, timedelta, date
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from faker import Faker
from app.database import SessionLocal, engine
from app.models.tasks import Task, TaskStage, State, StageTemplate, TemplateStage
from app.models.user import User

fake = Faker()

# Realistic task data organized by business domain
TASK_TEMPLATES = {
    "Software Development": [
        ("User Authentication System", "Implement secure JWT-based authentication with role management"),
        ("Mobile App UI Redesign", "Modernize the mobile interface with new design system"),
        ("API Performance Optimization", "Reduce API response times and improve caching"),
        ("Database Migration to PostgreSQL", "Migrate from legacy system to PostgreSQL"),
        ("Microservices Architecture Setup", "Break monolith into domain-driven microservices"),
        ("CI/CD Pipeline Implementation", "Automate testing and deployment workflows"),
        ("Real-time Chat Feature", "Add WebSocket-based chat for user communication"),
        ("Payment Gateway Integration", "Integrate Stripe for subscription payments"),
        ("Admin Dashboard Development", "Build comprehensive analytics dashboard for admins"),
        ("Mobile App Push Notifications", "Implement FCM-based push notification system"),
    ],
    "Marketing": [
        ("Q1 Digital Marketing Campaign", "Launch multi-channel campaign for new product line"),
        ("Social Media Strategy Revamp", "Develop new content strategy across all platforms"),
        ("Email Newsletter Automation", "Set up drip campaigns for customer segments"),
        ("Brand Identity Refresh", "Update logo, colors, and brand guidelines"),
        ("Influencer Partnership Program", "Identify and onboard key industry influencers"),
        ("Content Calendar Planning", "Plan 3-month content across blog, social, email"),
        ("SEO Optimization Project", "Improve organic search rankings for key terms"),
        ("Customer Testimonial Campaign", "Collect and showcase customer success stories"),
        ("Product Launch Event", "Organize virtual launch event for flagship product"),
        ("Marketing Analytics Dashboard", "Build reporting dashboard for campaign metrics"),
    ],
    "Operations": [
        ("Server Infrastructure Upgrade", "Migrate to cloud infrastructure with auto-scaling"),
        ("Disaster Recovery Plan", "Develop and test comprehensive backup strategy"),
        ("Security Audit and Compliance", "Complete SOC 2 compliance certification"),
        ("Office Space Renovation", "Redesign workspace for hybrid work model"),
        ("Vendor Management System", "Implement centralized vendor tracking platform"),
        ("IT Asset Management", "Catalog and track all company hardware and licenses"),
        ("Network Security Enhancement", "Deploy zero-trust network architecture"),
        ("Customer Support Portal", "Build self-service knowledge base and ticketing"),
        ("Inventory Management System", "Implement automated inventory tracking"),
        ("Business Continuity Testing", "Test and validate disaster recovery procedures"),
    ],
    "HR": [
        ("Annual Performance Review Process", "Conduct company-wide performance evaluations"),
        ("Employee Onboarding Program", "Develop comprehensive onboarding experience"),
        ("Diversity and Inclusion Initiative", "Launch DEI training and hiring programs"),
        ("Benefits Package Review", "Evaluate and enhance employee benefits offerings"),
        ("Remote Work Policy Development", "Create guidelines for distributed workforce"),
        ("Learning and Development Platform", "Set up online training and certification system"),
        ("Employee Engagement Survey", "Conduct quarterly satisfaction and culture assessment"),
        ("Recruitment Process Optimization", "Streamline hiring with new ATS system"),
        ("Workplace Culture Program", "Organize team-building and culture events"),
        ("Compensation Benchmarking Study", "Research and adjust salary bands for competitiveness"),
    ],
    "Finance": [
        ("Annual Budget Planning", "Prepare FY2026 departmental budgets and forecasts"),
        ("Expense Management System", "Implement automated expense reporting platform"),
        ("Financial Reporting Automation", "Automate monthly financial close process"),
        ("Tax Compliance Audit", "Prepare for annual tax filing and compliance review"),
        ("Revenue Recognition Analysis", "Review revenue streams and accounting treatment"),
        ("Cash Flow Optimization", "Improve working capital and payment terms"),
        ("Investment Portfolio Review", "Assess and rebalance company investment strategy"),
        ("Procurement Cost Reduction", "Analyze and negotiate vendor contracts for savings"),
        ("Financial Dashboard Development", "Build real-time executive financial dashboards"),
        ("Grant Funding Application", "Apply for government innovation grant program"),
    ],
    "Product": [
        ("Customer Feedback Analysis", "Analyze user research and prioritize feature requests"),
        ("Product Roadmap Planning Q2", "Define and sequence next quarter deliverables"),
        ("User Analytics Implementation", "Set up product analytics and tracking events"),
        ("Feature: Advanced Search", "Design and implement multi-criteria search functionality"),
        ("Mobile Experience Optimization", "Improve mobile web performance and UX"),
        ("Beta Testing Program", "Establish early access program for new features"),
        ("Competitive Analysis Report", "Research competitor features and market positioning"),
        ("Product Documentation Update", "Refresh user guides and API documentation"),
        ("A/B Testing Framework", "Implement experimentation platform for features"),
        ("Customer Journey Mapping", "Document and optimize key user workflows"),
    ],
}

STAGE_TEMPLATES_DATA = [
    {
        "name": "Software Development Workflow",
        "description": "Standard SDLC stages for development projects",
        "stages": [
            ("Planning & Requirements", 8.0, 1),
            ("Development", 20.0, 2),
            ("Testing & QA", 10.0, 3),
            ("Deployment", 4.0, 4),
        ]
    },
    {
        "name": "Content Creation Process",
        "description": "Workflow for marketing and content production",
        "stages": [
            ("Research & Ideation", 5.0, 1),
            ("Drafting", 8.0, 2),
            ("Review & Editing", 4.0, 3),
            ("Publishing", 2.0, 4),
        ]
    },
    {
        "name": "Marketing Campaign",
        "description": "Standard campaign execution workflow",
        "stages": [
            ("Strategy & Planning", 10.0, 1),
            ("Creative Development", 15.0, 2),
            ("Campaign Execution", 12.0, 3),
            ("Analysis & Reporting", 6.0, 4),
        ]
    },
    {
        "name": "Product Launch",
        "description": "New product or feature launch process",
        "stages": [
            ("Market Research", 12.0, 1),
            ("Development", 25.0, 2),
            ("Beta Testing", 8.0, 3),
            ("Launch & Marketing", 10.0, 4),
        ]
    },
]


def clear_existing_data(db):
    """Clear all existing data except states"""
    print("🗑️  Clearing existing data...")
    
    # Delete in order respecting foreign keys
    db.query(TaskStage).delete()
    db.query(Task).delete()
    db.query(TemplateStage).delete()
    db.query(StageTemplate).delete()
    db.query(User).delete()
    
    db.commit()
    print("✅ Existing data cleared")


def ensure_states(db):
    """Ensure required states exist"""
    print("🔧 Ensuring states exist...")
    
    states_data = [
        (1, "pending", "Task is waiting to start"),
        (2, "in-progress", "Task is currently being worked on"),
        (3, "completed", "Task is finished"),
        (4, "overdue", "Task passed due date without completion"),
    ]
    
    for state_id, state_name, description in states_data:
        existing = db.query(State).filter_by(state_id=state_id).first()
        if not existing:
            state = State(state_id=state_id, state_name=state_name, description=description)
            db.add(state)
    
    db.commit()
    print("✅ States verified")


def create_users(db, count=18):
    """Create realistic users with actual names"""
    print(f"👥 Creating {count} realistic users...")
    
    users = []
    used_usernames = set()
    used_emails = set()
    
    for i in range(count):
        # Generate unique username and email
        while True:
            full_name = fake.name()
            first_name = full_name.split()[0].lower()
            last_name = full_name.split()[-1].lower()
            username = f"{first_name}.{last_name}"
            
            if username not in used_usernames:
                used_usernames.add(username)
                break
        
        while True:
            email = fake.email()
            if email not in used_emails:
                used_emails.add(email)
                break
        
        user = User(
            username=username,
            email=email,
            full_name=full_name
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    # Refresh to get IDs
    for user in users:
        db.refresh(user)
    
    print(f"✅ Created {len(users)} users")
    return users


def create_stage_templates(db):
    """Create reusable stage templates"""
    print("📋 Creating stage templates...")
    
    templates = []
    for template_data in STAGE_TEMPLATES_DATA:
        template = StageTemplate(
            template_name=template_data["name"],
            description=template_data["description"]
        )
        db.add(template)
        db.flush()  # Get ID
        
        for stage_name, est_hours, order_num in template_data["stages"]:
            template_stage = TemplateStage(
                template_id=template.template_id,
                stage_name=stage_name,
                estimated_time_hours=est_hours,
                order_number=order_num
            )
            db.add(template_stage)
        
        templates.append(template)
    
    db.commit()
    print(f"✅ Created {len(templates)} stage templates")
    return templates


def create_realistic_tasks(db, users, templates):
    """Create 50+ realistic tasks with varied statuses and priorities"""
    print("📝 Creating 50+ realistic tasks...")
    
    # Get state IDs
    states = {s.state_name: s.state_id for s in db.query(State).all()}
    
    # Flatten all task templates
    all_tasks = []
    for domain, tasks in TASK_TEMPLATES.items():
        all_tasks.extend([(domain, name, desc) for name, desc in tasks])
    
    # We need at least 50, use all 60 available
    random.shuffle(all_tasks)
    tasks_to_create = all_tasks[:55]  # Create 55 tasks for good measure
    
    # Status distribution for realistic visualization
    # 30 completed (historical), 12 in-progress, 8 pending, 5 overdue
    status_mix = (
        [("completed", states["completed"])] * 30 +
        [("in-progress", states["in-progress"])] * 12 +
        [("pending", states["pending"])] * 8 +
        [("overdue", states["overdue"])] * 5
    )
    random.shuffle(status_mix)
    
    # Priority distribution: 30% high, 50% medium, 20% low
    priority_mix = (
        ["high"] * 17 +
        ["medium"] * 28 +
        ["low"] * 10
    )
    random.shuffle(priority_mix)
    
    created_tasks = []
    today = date.today()
    
    for idx, (domain, task_name, task_desc) in enumerate(tasks_to_create):
        status_name, status_id = status_mix[idx]
        priority = priority_mix[idx]
        assigned_user = random.choice(users)
        
        # Date logic based on status
        if status_name == "completed":
            # Historical: completed 1-180 days ago
            days_ago = random.randint(1, 180)
            completed_date = today - timedelta(days=days_ago)
            created_date = completed_date - timedelta(days=random.randint(5, 15))
            # Due date could be before or after completion (for variance analysis)
            delay = random.randint(-3, 7)  # Can be early or late
            due_date = completed_date - timedelta(days=delay)
        elif status_name == "overdue":
            # Overdue: past due date, not completed
            days_overdue = random.randint(1, 14)
            due_date = today - timedelta(days=days_overdue)
            created_date = due_date - timedelta(days=random.randint(5, 20))
            completed_date = None
        else:
            # Pending or in-progress: future due date
            days_ahead = random.randint(1, 30)
            due_date = today + timedelta(days=days_ahead)
            created_date = today - timedelta(days=random.randint(0, 10))
            completed_date = None
        
        task = Task(
            name=task_name,
            description=task_desc,
            status_state_id=status_id,
            due_date=due_date,
            completed_date=completed_date,
            priority=priority,
            assigned_user_id=assigned_user.user_id,
            created_at=datetime.combine(created_date, datetime.min.time())
        )
        db.add(task)
        db.flush()  # Get task ID
        
        # Add stages to task
        # Use template for some tasks, custom for others
        use_template = random.random() < 0.6  # 60% use templates
        
        if use_template and templates:
            template = random.choice(templates)
            for ts in sorted(db.query(TemplateStage).filter_by(template_id=template.template_id).all(), 
                           key=lambda x: x.order_number):
                # Determine stage status based on task status
                if status_name == "completed":
                    stage_status_id = states["completed"]
                    stage_completed_date = completed_date
                    stage_start_date = completed_date - timedelta(days=random.randint(1, 5))
                    # Add variance to actual time
                    actual_hours = ts.estimated_time_hours * random.uniform(0.7, 1.4)
                elif status_name == "in-progress":
                    # Mix of completed and in-progress stages
                    if ts.order_number == 1:
                        stage_status_id = states["completed"]
                        stage_completed_date = today - timedelta(days=random.randint(1, 5))
                        stage_start_date = stage_completed_date - timedelta(days=random.randint(1, 3))
                        actual_hours = ts.estimated_time_hours * random.uniform(0.8, 1.3)
                    elif ts.order_number == 2:
                        stage_status_id = states["in-progress"]
                        stage_completed_date = None
                        stage_start_date = today - timedelta(days=random.randint(1, 5))
                        actual_hours = ts.estimated_time_hours * random.uniform(0.3, 0.7)
                    else:
                        stage_status_id = states["pending"]
                        stage_completed_date = None
                        stage_start_date = None
                        actual_hours = None
                else:
                    # Pending or overdue: all stages pending
                    stage_status_id = states["pending"]
                    stage_completed_date = None
                    stage_start_date = None
                    actual_hours = None
                
                stage = TaskStage(
                    task_id=task.task_id,
                    stage_name=ts.stage_name,
                    estimated_time_hours=ts.estimated_time_hours,
                    actual_time_hours=actual_hours,
                    status_state_id=stage_status_id,
                    order_number=ts.order_number,
                    start_date=stage_start_date,
                    completed_date=stage_completed_date
                )
                db.add(stage)
        else:
            # Create custom stages
            custom_stages = [
                ("Initial Setup", random.uniform(3, 8)),
                ("Main Implementation", random.uniform(10, 25)),
                ("Review & Testing", random.uniform(5, 12)),
            ]
            
            for order_num, (stage_name, est_hours) in enumerate(custom_stages, 1):
                # Similar status logic as template
                if status_name == "completed":
                    stage_status_id = states["completed"]
                    stage_completed_date = completed_date
                    stage_start_date = completed_date - timedelta(days=random.randint(1, 4))
                    actual_hours = est_hours * random.uniform(0.7, 1.4)
                elif status_name == "in-progress" and order_num <= 1:
                    stage_status_id = states["completed"]
                    stage_completed_date = today - timedelta(days=random.randint(1, 4))
                    stage_start_date = stage_completed_date - timedelta(days=random.randint(1, 3))
                    actual_hours = est_hours * random.uniform(0.8, 1.3)
                elif status_name == "in-progress" and order_num == 2:
                    stage_status_id = states["in-progress"]
                    stage_completed_date = None
                    stage_start_date = today - timedelta(days=random.randint(1, 5))
                    actual_hours = est_hours * random.uniform(0.3, 0.6)
                else:
                    stage_status_id = states["pending"]
                    stage_completed_date = None
                    stage_start_date = None
                    actual_hours = None
                
                stage = TaskStage(
                    task_id=task.task_id,
                    stage_name=stage_name,
                    estimated_time_hours=est_hours,
                    actual_time_hours=actual_hours,
                    status_state_id=stage_status_id,
                    order_number=order_num,
                    start_date=stage_start_date,
                    completed_date=stage_completed_date
                )
                db.add(stage)
        
        created_tasks.append(task)
    
    db.commit()
    print(f"✅ Created {len(created_tasks)} realistic tasks with stages")
    return created_tasks


def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("🚀 REALISTIC MOCK DATA GENERATION SCRIPT")
    print("="*60 + "\n")
    
    db = SessionLocal()
    
    try:
        # Step 1: Clear existing data
        clear_existing_data(db)
        
        # Step 2: Ensure states exist
        ensure_states(db)
        
        # Step 3: Create users
        users = create_users(db, count=18)
        
        # Step 4: Create stage templates
        templates = create_stage_templates(db)
        
        # Step 5: Create realistic tasks
        tasks = create_realistic_tasks(db, users, templates)
        
        print("\n" + "="*60)
        print("✨ SUCCESS! Database populated with realistic data")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"   - Users: {len(users)}")
        print(f"   - Stage Templates: {len(templates)}")
        print(f"   - Tasks: {len(tasks)}")
        print(f"   - Task Stages: {db.query(TaskStage).count()}")
        print("\n✅ Ready for visualization and testing!\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
