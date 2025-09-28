"""
الملف الرئيسي لتشغيل البوت
Main Bot Application File
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings, LOGGING_CONFIG
from database import init_database, db_manager
from handlers import setup_handlers, error_handler
from scheduler import bot_scheduler
from payments import start_webhook_server


# إعداد التسجيل
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class TelegramBot:
    """فئة البوت الرئيسية"""
    
    def __init__(self):
        # إنشاء البوت
        self.bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # إنشاء الموزع مع تخزين الذاكرة
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # تسجيل معالج الأخطاء
        self.dp.errors.register(error_handler)
        
        logger.info("Bot initialized successfully")
    
    async def startup(self):
        """إجراءات بدء التشغيل"""
        try:
            # تهيئة قاعدة البيانات
            logger.info("Initializing database...")
            await init_database()
            
            # إعداد المعالجات
            logger.info("Setting up handlers...")
            setup_handlers(self.dp, self.bot)
            
            # بدء المجدول
            logger.info("Starting scheduler...")
            await bot_scheduler.start()
            
            # إعداد المديرين الافتراضيين
            await self.setup_default_admins()
            
            # إعداد القنوات الافتراضية
            await self.setup_default_channels()
            
            logger.info("Bot startup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during startup: {e}")
            raise
    
    async def shutdown(self):
        """إجراءات إيقاف التشغيل"""
        try:
            logger.info("Shutting down bot...")
            
            # إيقاف المجدول
            await bot_scheduler.stop()
            
            # إغلاق قاعدة البيانات
            await db_manager.close()
            
            # إغلاق جلسة البوت
            await self.bot.session.close()
            
            logger.info("Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def setup_default_admins(self):
        """إعداد المديرين الافتراضيين"""
        try:
            from database import user_service
            
            for admin_id in settings.ADMIN_USER_IDS:
                await user_service.set_admin_status(admin_id, True)
                logger.info(f"Set admin status for user {admin_id}")
                
        except Exception as e:
            logger.error(f"Error setting up default admins: {e}")
    
    async def setup_default_channels(self):
        """إعداد القنوات الافتراضية"""
        try:
            from database import channel_service
            
            # إعداد القناة العامة
            if settings.PUBLIC_CHANNEL_ID:
                try:
                    chat_info = await self.bot.get_chat(settings.PUBLIC_CHANNEL_ID)
                    await channel_service.create_or_update_channel(
                        telegram_channel_id=settings.PUBLIC_CHANNEL_ID,
                        channel_data={
                            'channel_username': chat_info.username,
                            'channel_title': chat_info.title,
                            'channel_type': 'public',
                            'description_ar': 'القناة العامة المجانية',
                            'description_en': 'Free public channel',
                            'is_active': True
                        }
                    )
                    logger.info(f"Setup public channel: {chat_info.title}")
                except Exception as e:
                    logger.warning(f"Could not setup public channel: {e}")
            
            # إعداد القناة الخاصة
            if settings.PRIVATE_CHANNEL_ID:
                try:
                    chat_info = await self.bot.get_chat(settings.PRIVATE_CHANNEL_ID)
                    await channel_service.create_or_update_channel(
                        telegram_channel_id=settings.PRIVATE_CHANNEL_ID,
                        channel_data={
                            'channel_username': chat_info.username,
                            'channel_title': chat_info.title,
                            'channel_type': 'private',
                            'description_ar': 'القناة الخاصة المدفوعة',
                            'description_en': 'Paid private channel',
                            'is_active': True
                        }
                    )
                    logger.info(f"Setup private channel: {chat_info.title}")
                except Exception as e:
                    logger.warning(f"Could not setup private channel: {e}")
                    
        except Exception as e:
            logger.error(f"Error setting up default channels: {e}")
    
    async def run(self):
        """تشغيل البوت"""
        try:
            # إجراءات بدء التشغيل
            await self.startup()
            
            # بدء تشغيل البوت
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise
        finally:
            # إجراءات إيقاف التشغيل
            await self.shutdown()


async def run_webhook_server():
    """تشغيل خادم webhook في الخلفية"""
    try:
        if settings.WEBHOOK_HOST and settings.WEBHOOK_PORT:
            logger.info("Starting webhook server...")
            await start_webhook_server()
    except Exception as e:
        logger.error(f"Error starting webhook server: {e}")


async def main():
    """الدالة الرئيسية"""
    try:
        # إنشاء البوت
        bot = TelegramBot()
        
        # تشغيل البوت وخادم webhook معاً
        if settings.WEBHOOK_HOST:
            # تشغيل البوت وخادم webhook بشكل متوازي
            await asyncio.gather(
                bot.run(),
                run_webhook_server()
            )
        else:
            # تشغيل البوت فقط
            await bot.run()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # تشغيل البوت
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)