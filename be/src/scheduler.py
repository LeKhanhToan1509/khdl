import schedule
import time
import threading
from datetime import datetime, timedelta
import requests
from pymongo import MongoClient
import json
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JobCrawlScheduler:
    def __init__(self):
        # MongoDB connection
        self.client = MongoClient("mongodb://root:123456@localhost:27017/")
        self.db = self.client.job_data
        self.scheduler_collection = self.db.scheduler_status
        
        # Crawl settings
        self.crawl_time = "09:00"  # Crawl at 9:00 AM daily
        self.is_running = False
        
    def init_scheduler_status(self):
        """Initialize scheduler status in database"""
        try:
            # Check if status exists
            status = self.scheduler_collection.find_one({"type": "daily_crawl"})
            if not status:
                # Create initial status
                initial_status = {
                    "type": "daily_crawl",
                    "last_crawl_date": None,
                    "next_crawl_time": f"{datetime.now().strftime('%Y-%m-%d')} {self.crawl_time}:00",
                    "crawled_today": False,
                    "crawl_status": "waiting",
                    "last_crawl_records": 0,
                    "total_records": 0,
                    "updated_at": datetime.now()
                }
                self.scheduler_collection.insert_one(initial_status)
                logger.info("Initialized scheduler status")
        except Exception as e:
            logger.error(f"Error initializing scheduler status: {e}")
    
    def check_crawled_today(self) -> bool:
        """Check if data was crawled today"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            status = self.scheduler_collection.find_one({"type": "daily_crawl"})
            
            if status and status.get('last_crawl_date'):
                last_crawl = status['last_crawl_date']
                if isinstance(last_crawl, str):
                    last_crawl_date = last_crawl.split(' ')[0]  # Get date part
                else:
                    last_crawl_date = last_crawl.strftime('%Y-%m-%d')
                
                return last_crawl_date == today
            return False
        except Exception as e:
            logger.error(f"Error checking crawl status: {e}")
            return False
    
    def update_crawl_status(self, status: str, records: int = 0):
        """Update crawl status in database"""
        try:
            now = datetime.now()
            update_data = {
                "crawl_status": status,
                "updated_at": now
            }
            
            if status == "completed":
                update_data.update({
                    "last_crawl_date": now.strftime('%Y-%m-%d %H:%M:%S'),
                    "crawled_today": True,
                    "last_crawl_records": records,
                    "next_crawl_time": (now + timedelta(days=1)).strftime('%Y-%m-%d') + f" {self.crawl_time}:00"
                })
            elif status == "running":
                update_data["crawled_today"] = False
            
            self.scheduler_collection.update_one(
                {"type": "daily_crawl"},
                {"$set": update_data}
            )
            logger.info(f"Updated crawl status to: {status}")
        except Exception as e:
            logger.error(f"Error updating crawl status: {e}")
    
    def crawl_today_jobs(self):
        """Crawl jobs posted today from all categories"""
        logger.info("Starting daily crawl job...")
        self.update_crawl_status("running")
        
        total_crawled = 0
        categories = ["python-developer", "java-developer", "react-developer", 
                     "nodejs-developer", "php-developer", "dotnet-developer",
                     "android-developer", "ios-developer", "devops-engineer"]
        
        try:
            for category in categories:
                try:
                    # Simulate crawling from page 1 only for today's jobs
                    # In real implementation, you would call your actual crawl function
                    crawled_count = self.crawl_category_today(category)
                    total_crawled += crawled_count
                    logger.info(f"Crawled {crawled_count} jobs from {category}")
                    
                    # Small delay between categories
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error crawling {category}: {e}")
                    continue
            
            self.update_crawl_status("completed", total_crawled)
            logger.info(f"Daily crawl completed. Total records: {total_crawled}")
            
        except Exception as e:
            logger.error(f"Error in daily crawl: {e}")
            self.update_crawl_status("error")
    
    def crawl_category_today(self, category: str) -> int:
        """Crawl today's jobs for a specific category (page 1 only)"""
        try:
            # This would be replaced with your actual crawl logic
            # For now, simulate crawling
            
            # Check if collection exists, if not create it
            collection = self.db[category.replace('-', '_')]
            
            # Simulate getting today's jobs (in real implementation, filter by date)
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Simulate crawled data (replace with actual crawl logic)
            sample_jobs = [
                {
                    "title": f"Sample {category} Job {i}",
                    "company": f"Company {i}",
                    "location": "Hà Nội" if i % 2 == 0 else "TP.HCM",
                    "salary_avg_million_vnd": 15 + (i * 2),
                    "experience_years": f"{i} năm" if i > 0 else "Không yêu cầu",
                    "skills": ["Python", "Django", "FastAPI"] if "python" in category else ["Java", "Spring"],
                    "category": category.replace('-', '_'),
                    "update_date": datetime.now(),
                    "crawl_date": today,
                    "is_today": True
                }
                for i in range(5)  # Simulate 5 jobs per category
            ]
            
            # Insert only if not already exists today
            existing_today = collection.count_documents({
                "crawl_date": today,
                "is_today": True
            })
            
            if existing_today == 0:
                collection.insert_many(sample_jobs)
                return len(sample_jobs)
            else:
                logger.info(f"Today's jobs already exist for {category}")
                return 0
                
        except Exception as e:
            logger.error(f"Error crawling category {category}: {e}")
            return 0
    
    def get_next_crawl_time(self) -> Dict[str, Any]:
        """Get time until next crawl"""
        try:
            now = datetime.now()
            
            # Check if crawled today
            crawled_today = self.check_crawled_today()
            
            if crawled_today:
                # Next crawl is tomorrow
                tomorrow = now + timedelta(days=1)
                next_crawl = datetime.strptime(f"{tomorrow.strftime('%Y-%m-%d')} {self.crawl_time}:00", '%Y-%m-%d %H:%M:%S')
            else:
                # Next crawl is today if time hasn't passed, otherwise tomorrow
                today_crawl_time = datetime.strptime(f"{now.strftime('%Y-%m-%d')} {self.crawl_time}:00", '%Y-%m-%d %H:%M:%S')
                
                if now < today_crawl_time:
                    next_crawl = today_crawl_time
                else:
                    tomorrow = now + timedelta(days=1)
                    next_crawl = datetime.strptime(f"{tomorrow.strftime('%Y-%m-%d')} {self.crawl_time}:00", '%Y-%m-%d %H:%M:%S')
            
            time_diff = next_crawl - now
            
            return {
                "next_crawl_time": next_crawl.strftime('%Y-%m-%d %H:%M:%S'),
                "time_until_crawl": {
                    "days": time_diff.days,
                    "hours": time_diff.seconds // 3600,
                    "minutes": (time_diff.seconds % 3600) // 60,
                    "seconds": time_diff.seconds % 60,
                    "total_seconds": int(time_diff.total_seconds())
                },
                "crawled_today": crawled_today,
                "current_time": now.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error calculating next crawl time: {e}")
            return {
                "error": str(e),
                "crawled_today": False,
                "current_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def job_function(self):
        """The actual job function that runs daily"""
        if not self.check_crawled_today():
            self.crawl_today_jobs()
        else:
            logger.info("Already crawled today, skipping...")
    
    def start_scheduler(self):
        """Start the scheduler"""
        logger.info(f"Starting job scheduler - Daily crawl at {self.crawl_time}")
        
        # Initialize status
        self.init_scheduler_status()
        
        # Schedule daily job
        schedule.every().day.at(self.crawl_time).do(self.job_function)
        
        # Also allow manual trigger if not crawled today
        self.is_running = True
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        # Run scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Job scheduler started successfully")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        schedule.clear()
        logger.info("Job scheduler stopped")
    
    def manual_crawl(self):
        """Manual trigger for crawl job"""
        if not self.check_crawled_today():
            self.crawl_today_jobs()
            return True
        return False

# Global scheduler instance
scheduler_instance = JobCrawlScheduler()