"""
المجدول للتنبيهات والمهام التلقائية
Scheduler for Notifications and Automated Tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import settings
from database import (
    db_manager, subscription_service, user_service, 
    ScheduledTask, Subscription, User, Analytics
)
from localization import translator, get_user_language


class BotScheduler:
    """مجدول البوت"""
    
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.logger = logging.getLogger(__name__)
        
        # إعداد المجدول
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.SCHEDULER_TIMEZONE
        )
    
    async def start(self):
        """بدء المجدول"""
        self.scheduler.start()
        self.logger.info("Scheduler started")
        
        # جدولة المهام الدورية
        await self.schedule_recurring_tasks()
    
    async def stop(self):
        """إيقاف المجدول"""
        self.scheduler.shutdown()
        self.logger.info("Scheduler stopped")
    
    async def schedule_recurring_tasks(self):
        """جدولة المهام الدورية"""
        
        # فحص الاشتراكات المنتهية كل ساعة
        self.scheduler.add_job(
            func=self.check_expired_subscriptions,
            trigger=IntervalTrigger(hours=1),
            id='check_expired_subscriptions',
            replace_existing=True
        )
        
        # فحص الاشتراكات التي ستنتهي قريباً كل 6 ساعات
        self.scheduler.add_job(
            func=self.check_expiring_subscriptions,
            trigger=IntervalTrigger(hours=6),
            id='check_expiring_subscriptions',
            replace_existing=True
        )
        
        # تنظيف البيانات المؤقتة يومياً في الساعة 2 صباحاً
        self.scheduler.add_job(
            func=self.cleanup_temporary_data,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_cleanup',
            replace_existing=True
        )
        
        # إنشاء تقارير يومية في الساعة 9 صباحاً
        self.scheduler.add_job(
            func=self.generate_daily_reports,
            trigger=CronTrigger(hour=9, minute=0),
            id='daily_reports',
            replace_existing=True
        )
        
        self.logger.info("Recurring tasks scheduled")
    
    async def send_expiry_reminder(self, subscription_id: int):
        """إرسال تذكير انتهاء الاشتراك"""
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                
                # الحصول على تفاصيل الاشتراك
                result = await session.execute(
                    select(Subscription)
                    .options(selectinload(Subscription.user))
                    .options(selectinload(Subscription.plan))
                    .where(Subscription.id == subscription_id)
                )
                subscription = result.scalar_one_or_none()
                
                if not subscription or subscription.status != "active":
                    return
                
                user = subscription.user
                plan = subscription.plan
                language = user.preferred_language or "en"
                
                # حساب الساعات المتبقية
                time_left = subscription.end_date - datetime.utcnow()
                hours_left = int(time_left.total_seconds() / 3600)
                
                # إنشاء الرسالة
                message = translator.get_text(
                    "warning_subscription_expiring",
                    language,
                    plan_name=plan.name_ar if language == "ar" else plan.name_en,
                    hours=hours_left,
                    end_date=subscription.end_date.strftime("%Y-%m-%d %H:%M")
                )
                
                # إرسال الرسالة
                if self.bot:
                    from keyboards import keyboard_manager
                    keyboard = keyboard_manager.get_renewal_reminder_keyboard(
                        subscription_id, language
                    )
                    
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        reply_markup=keyboard
                    )
                
                self.logger.info(f"Sent expiry reminder to user {user.telegram_id}")
                
        except Exception as e:
            self.logger.error(f"Error sending expiry reminder: {e}")
    
    async def auto_kick_user(self, subscription_id: int):
        """طرد المستخدم تلقائياً عند انتهاء الاشتراك"""
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select, update
                from sqlalchemy.orm import selectinload
                
                # الحصول على تفاصيل الاشتراك
                result = await session.execute(
                    select(Subscription)
                    .options(selectinload(Subscription.user))
                    .options(selectinload(Subscription.plan))
                    .options(selectinload(Subscription.channel))
                    .where(Subscription.id == subscription_id)
                )
                subscription = result.scalar_one_or_none()
                
                if not subscription:
                    return
                
                user = subscription.user
                channel = subscription.channel
                plan = subscription.plan
                
                # التحقق من انتهاء الاشتراك
                if subscription.end_date > datetime.utcnow():
                    return
                
                try:
                    # طرد المستخدم من القناة
                    if self.bot and channel:
                        await self.bot.ban_chat_member(
                            chat_id=channel.telegram_channel_id,
                            user_id=user.telegram_id
                        )
                        
                        # إلغاء الحظر فوراً للسماح بالعودة لاحقاً
                        await self.bot.unban_chat_member(
                            chat_id=channel.telegram_channel_id,
                            user_id=user.telegram_id
                        )
                    
                    # تحديث حالة الاشتراك
                    await session.execute(
                        update(Subscription)
                        .where(Subscription.id == subscription_id)
                        .values(
                            status="expired",
                            updated_at=datetime.utcnow()
                        )
                    )
                    
                    # إرسال رسالة وداع
                    language = user.preferred_language or "en"
                    farewell_message = translator.get_text(
                        "info_subscription_expired",
                        language,
                        plan_name=plan.name_ar if language == "ar" else plan.name_en
                    )
                    
                    if self.bot:
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=farewell_message
                        )
                    
                    await session.commit()
                    self.logger.info(f"Auto kicked user {user.telegram_id}")
                    
                except Exception as kick_error:
                    self.logger.error(f"Error kicking user: {kick_error}")
                
        except Exception as e:
            self.logger.error(f"Error in auto kick: {e}")
    
    async def check_expired_subscriptions(self):
        """فحص الاشتراكات المنتهية"""
        try:
            expired_subscriptions = await subscription_service.get_expired_subscriptions()
            
            for subscription in expired_subscriptions:
                await self.auto_kick_user(subscription.id)
            
            self.logger.info(f"Processed {len(expired_subscriptions)} expired subscriptions")
            
        except Exception as e:
            self.logger.error(f"Error checking expired subscriptions: {e}")
    
    async def check_expiring_subscriptions(self):
        """فحص الاشتراكات التي ستنتهي قريباً"""
        try:
            expiring_subscriptions = await subscription_service.get_expiring_subscriptions(24)
            
            for subscription in expiring_subscriptions:
                await self.send_expiry_reminder(subscription.id)
            
            self.logger.info(f"Processed {len(expiring_subscriptions)} expiring subscriptions")
            
        except Exception as e:
            self.logger.error(f"Error checking expiring subscriptions: {e}")
    
    async def cleanup_temporary_data(self):
        """تنظيف البيانات المؤقتة"""
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import delete
                
                # حذف المهام المكتملة القديمة (أكثر من 30 يوم)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                await session.execute(
                    delete(ScheduledTask)
                    .where(
                        ScheduledTask.status == "completed",
                        ScheduledTask.executed_at < cutoff_date
                    )
                )
                
                await session.commit()
                
            self.logger.info("Temporary data cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error in cleanup: {e}")
    
    async def generate_daily_reports(self):
        """إنشاء التقارير اليومية"""
        try:
            today = datetime.now().date()
            
            # حساب الإحصائيات اليومية
            async with db_manager.get_session() as session:
                from sqlalchemy import select, func
                from database import Payment
                
                # المستخدمين الجدد
                new_users_result = await session.execute(
                    select(func.count(User.id))
                    .where(func.date(User.registration_date) == today)
                )
                new_users = new_users_result.scalar() or 0
                
                # الاشتراكات الجديدة
                new_subs_result = await session.execute(
                    select(func.count(Subscription.id))
                    .where(func.date(Subscription.created_at) == today)
                )
                new_subscriptions = new_subs_result.scalar() or 0
                
                # الإيرادات اليومية
                revenue_result = await session.execute(
                    select(func.sum(Payment.amount))
                    .where(
                        func.date(Payment.completed_at) == today,
                        Payment.status == "completed"
                    )
                )
                revenue = float(revenue_result.scalar() or 0)
                
                # حفظ الإحصائيات
                analytics_entries = [
                    Analytics(
                        metric_name="daily_new_users",
                        metric_value=new_users,
                        metric_date=today
                    ),
                    Analytics(
                        metric_name="daily_new_subscriptions",
                        metric_value=new_subscriptions,
                        metric_date=today
                    ),
                    Analytics(
                        metric_name="daily_revenue",
                        metric_value=revenue,
                        metric_date=today
                    )
                ]
                
                session.add_all(analytics_entries)
                await session.commit()
            
            self.logger.info(f"Daily report generated")
            
        except Exception as e:
            self.logger.error(f"Error generating daily reports: {e}")
    
    async def save_scheduled_task(self, task_type: str, scheduled_time: datetime, 
                                subscription_id: int = None, user_id: int = None, 
                                task_data: Dict = None):
        """حفظ المهمة المجدولة في قاعدة البيانات"""
        try:
            async with db_manager.get_session() as session:
                task = ScheduledTask(
                    task_type=task_type,
                    user_id=user_id,
                    subscription_id=subscription_id,
                    scheduled_time=scheduled_time,
                    task_data=task_data or {}
                )
                
                session.add(task)
                await session.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving scheduled task: {e}")


# إنشاء مثيل المجدول العامة
bot_scheduler = BotScheduler()