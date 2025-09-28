"""
معالجات الرسائل للمستخدمين والإدارة
Message Handlers for Users and Administration
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from config import settings
from database import (
    user_service, subscription_service, channel_service, 
    plan_service, db_manager
)
from localization import translator, get_user_language, message_formatter
from keyboards import keyboard_manager
from payments import payment_manager
from scheduler import bot_scheduler


# إعداد التسجيل
logger = logging.getLogger(__name__)

# إنشاء الموجهات
user_router = Router()
admin_router = Router()
payment_router = Router()


# حالات المحادثة
class UserStates(StatesGroup):
    waiting_for_language = State()
    waiting_for_broadcast_message = State()
    waiting_for_plan_name = State()
    waiting_for_plan_price = State()
    waiting_for_plan_duration = State()


class BotHandlers:
    """معالجات البوت الرئيسية"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.logger = logging.getLogger(__name__)
    
    async def get_user_data(self, telegram_user) -> Dict[str, Any]:
        """الحصول على بيانات المستخدم"""
        user = await user_service.create_or_update_user(telegram_user)
        return {
            'id': user.id,
            'telegram_id': user.telegram_id,
            'preferred_language': user.preferred_language,
            'is_admin': user.is_admin,
            'username': user.username,
            'first_name': user.first_name
        }
    
    async def send_main_menu(self, chat_id: int, user_data: Dict[str, Any], 
                           message_id: int = None):
        """إرسال القائمة الرئيسية"""
        language = user_data.get('preferred_language', 'en')
        is_admin = user_data.get('is_admin', False)
        
        text = translator.get_text('main_menu', language)
        keyboard = keyboard_manager.get_main_menu_keyboard(language, is_admin)
        
        if message_id:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard
            )
        else:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )


# معالجات المستخدمين العاديين
@user_router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """معالج أمر البداية"""
    try:
        handlers = BotHandlers(message.bot)
        user_data = await handlers.get_user_data(message.from_user)
        
        # التحقق من وجود لغة محفوظة
        if not user_data.get('preferred_language'):
            # عرض اختيار اللغة
            text = translator.get_text('start', 'en')
            keyboard = keyboard_manager.get_language_selection_keyboard()
            
            await message.answer(text, reply_markup=keyboard)
            await state.set_state(UserStates.waiting_for_language)
        else:
            # عرض القائمة الرئيسية مباشرة
            await handlers.send_main_menu(message.chat.id, user_data)
            
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")


@user_router.callback_query(F.data.startswith("lang_"))
async def language_selection(callback: CallbackQuery, state: FSMContext):
    """معالج اختيار اللغة"""
    try:
        language = callback.data.split("_")[1]
        
        # تحديث لغة المستخدم
        await user_service.update_user_language(callback.from_user.id, language)
        
        # الحصول على بيانات المستخدم المحدثة
        handlers = BotHandlers(callback.bot)
        user_data = await handlers.get_user_data(callback.from_user)
        
        # إرسال رسالة التأكيد
        success_message = translator.get_text('success_language_changed', language)
        await callback.message.edit_text(success_message)
        
        # إرسال القائمة الرئيسية
        await asyncio.sleep(1)
        await handlers.send_main_menu(callback.message.chat.id, user_data)
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in language selection: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@user_router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """العودة للقائمة الرئيسية"""
    try:
        handlers = BotHandlers(callback.bot)
        user_data = await handlers.get_user_data(callback.from_user)
        
        await handlers.send_main_menu(
            callback.message.chat.id, 
            user_data, 
            callback.message.message_id
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in main menu callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@user_router.callback_query(F.data == "free_channels")
async def free_channels_callback(callback: CallbackQuery):
    """عرض القنوات المجانية"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        language = user_data.get('preferred_language', 'en')
        
        # الحصول على القنوات المجانية
        free_channels = await channel_service.get_channels_by_type("public")
        
        if free_channels:
            text = translator.get_text('free_channels_list', language)
            keyboard = keyboard_manager.get_free_channels_keyboard(
                [
                    {
                        'id': ch.id,
                        'channel_title': ch.channel_title,
                        'channel_username': ch.channel_username
                    }
                    for ch in free_channels
                ],
                language
            )
        else:
            text = "📭 لا توجد قنوات مجانية متاحة حالياً." if language == "ar" else "📭 No free channels available at the moment."
            keyboard = keyboard_manager.get_main_menu_keyboard(language, user_data.get('is_admin', False))
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in free channels callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@user_router.callback_query(F.data == "paid_subscriptions")
async def paid_subscriptions_callback(callback: CallbackQuery):
    """عرض الاشتراكات المدفوعة"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        language = user_data.get('preferred_language', 'en')
        
        # الحصول على خطط الاشتراك النشطة
        plans = await plan_service.get_active_plans()
        
        if plans:
            text = translator.get_text('subscription_plans', language)
            keyboard = keyboard_manager.get_subscription_plans_keyboard(
                [
                    {
                        'id': plan.id,
                        'name_ar': plan.name_ar,
                        'name_en': plan.name_en,
                        'price': float(plan.price),
                        'currency': plan.currency
                    }
                    for plan in plans
                ],
                language
            )
        else:
            text = "📭 لا توجد خطط اشتراك متاحة حالياً." if language == "ar" else "📭 No subscription plans available at the moment."
            keyboard = keyboard_manager.get_main_menu_keyboard(language, user_data.get('is_admin', False))
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in paid subscriptions callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@user_router.callback_query(F.data.startswith("select_plan_"))
async def select_plan_callback(callback: CallbackQuery):
    """اختيار خطة الاشتراك"""
    try:
        plan_id = int(callback.data.split("_")[2])
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        language = user_data.get('preferred_language', 'en')
        
        # الحصول على تفاصيل الخطة
        plan = await plan_service.get_plan_by_id(plan_id)
        
        if not plan:
            await callback.answer("❌ خطة غير صحيحة", show_alert=True)
            return
        
        # عرض تفاصيل الخطة وطرق الدفع
        plan_details = message_formatter.format_subscription_plan(
            {
                'name_ar': plan.name_ar,
                'name_en': plan.name_en,
                'description_ar': plan.description_ar,
                'description_en': plan.description_en,
                'price': float(plan.price),
                'currency': plan.currency,
                'duration_days': plan.duration_days
            },
            language
        )
        
        text = f"{plan_details}\n\n{translator.get_text('payment_instructions', language)}"
        keyboard = keyboard_manager.get_payment_methods_keyboard(plan_id, language)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in select plan callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@user_router.callback_query(F.data.startswith("pay_"))
async def payment_callback(callback: CallbackQuery):
    """معالج الدفع"""
    try:
        parts = callback.data.split("_")
        provider = parts[1]  # stripe أو paypal
        plan_id = int(parts[2])
        
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        language = user_data.get('preferred_language', 'en')
        
        # إنشاء الدفع
        payment_data = await payment_manager.create_payment(
            user_id=user_data['id'],
            plan_id=plan_id,
            provider=provider
        )
        
        # إرسال رابط الدفع
        text = f"{translator.get_text('payment_processing', language)}\n\n"
        text += f"💰 المبلغ: {payment_data['amount']} {payment_data['currency']}\n"
        text += f"📋 الخطة: {payment_data['plan_name']}\n\n"
        text += f"🔗 [اضغط هنا للدفع]({payment_data['payment_url']})"
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        await callback.answer("تم إنشاء رابط الدفع!" if language == "ar" else "Payment link created!")
        
    except Exception as e:
        logger.error(f"Error in payment callback: {e}")
        await callback.answer("❌ فشل في إنشاء الدفع", show_alert=True)


@user_router.callback_query(F.data == "my_subscriptions")
async def my_subscriptions_callback(callback: CallbackQuery):
    """عرض اشتراكات المستخدم"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        language = user_data.get('preferred_language', 'en')
        
        # الحصول على اشتراكات المستخدم
        subscriptions = await subscription_service.get_user_subscriptions(user_data['id'])
        
        if subscriptions:
            text = "📊 اشتراكاتي:\n\n" if language == "ar" else "📊 My Subscriptions:\n\n"
            
            for sub in subscriptions:
                sub_details = message_formatter.format_subscription_status(
                    {
                        'plan_name': sub.plan.name_ar if language == "ar" else sub.plan.name_en,
                        'status': sub.status,
                        'end_date': sub.end_date
                    },
                    language
                )
                text += f"{sub_details}\n\n"
        else:
            text = translator.get_text('no_active_subscriptions', language)
        
        keyboard = keyboard_manager.get_main_menu_keyboard(language, user_data.get('is_admin', False))
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in my subscriptions callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@user_router.callback_query(F.data == "settings")
async def settings_callback(callback: CallbackQuery):
    """إعدادات المستخدم"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        language = user_data.get('preferred_language', 'en')
        
        text = translator.get_text('btn_settings', language)
        keyboard = keyboard_manager.get_settings_keyboard(language)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


# معالجات الإدارة
@admin_router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    """لوحة التحكم الإدارية"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        
        # التحقق من صلاحية المدير
        if not user_data.get('is_admin', False):
            await callback.answer(
                translator.get_text('access_denied', user_data.get('preferred_language', 'en')),
                show_alert=True
            )
            return
        
        language = user_data.get('preferred_language', 'en')
        text = translator.get_text('admin_welcome', language)
        keyboard = keyboard_manager.get_admin_panel_keyboard(language)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin panel callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """إحصائيات البوت"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        
        if not user_data.get('is_admin', False):
            await callback.answer("❌ غير مصرح", show_alert=True)
            return
        
        language = user_data.get('preferred_language', 'en')
        
        # حساب الإحصائيات
        total_users = await user_service.get_users_count()
        active_subscriptions = len(await subscription_service.get_active_subscriptions())
        
        # حساب الإيرادات اليومية
        today = datetime.now().date()
        async with db_manager.get_session() as session:
            from sqlalchemy import select, func
            from database import Payment
            
            revenue_result = await session.execute(
                select(func.sum(Payment.amount))
                .where(
                    func.date(Payment.completed_at) == today,
                    Payment.status == "completed"
                )
            )
            daily_revenue = float(revenue_result.scalar() or 0)
            
            # المستخدمين الجدد اليوم
            new_users_result = await session.execute(
                select(func.count(User.id))
                .where(func.date(User.registration_date) == today)
            )
            new_users_today = new_users_result.scalar() or 0
        
        text = translator.get_text(
            'admin_stats',
            language,
            total_users=total_users,
            active_subscriptions=active_subscriptions,
            daily_revenue=daily_revenue,
            new_users_today=new_users_today
        )
        
        keyboard = keyboard_manager.get_admin_panel_keyboard(language)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin stats callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """البث الجماعي"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        
        if not user_data.get('is_admin', False):
            await callback.answer("❌ غير مصرح", show_alert=True)
            return
        
        language = user_data.get('preferred_language', 'en')
        text = translator.get_text('broadcast_prompt', language)
        
        await callback.message.edit_text(text)
        await state.set_state(UserStates.waiting_for_broadcast_message)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin broadcast callback: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


@admin_router.message(StateFilter(UserStates.waiting_for_broadcast_message))
async def process_broadcast_message(message: Message, state: FSMContext):
    """معالجة رسالة البث"""
    try:
        user_data = await BotHandlers(message.bot).get_user_data(message.from_user)
        
        if not user_data.get('is_admin', False):
            await message.answer("❌ غير مصرح")
            return
        
        language = user_data.get('preferred_language', 'en')
        broadcast_text = message.text
        
        # حفظ الرسالة في الحالة
        await state.update_data(broadcast_message=broadcast_text)
        
        # عرض تأكيد البث
        user_count = await user_service.get_users_count()
        confirm_text = translator.get_text(
            'broadcast_confirm',
            language,
            user_count=user_count
        )
        
        keyboard = keyboard_manager.get_broadcast_confirmation_keyboard(language)
        
        await message.answer(
            f"{confirm_text}\n\n📝 الرسالة:\n{broadcast_text}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error processing broadcast message: {e}")
        await message.answer("❌ حدث خطأ")


@admin_router.callback_query(F.data == "admin_send_broadcast")
async def send_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """إرسال البث الجماعي"""
    try:
        user_data = await BotHandlers(callback.bot).get_user_data(callback.from_user)
        
        if not user_data.get('is_admin', False):
            await callback.answer("❌ غير مصرح", show_alert=True)
            return
        
        # الحصول على الرسالة من الحالة
        state_data = await state.get_data()
        broadcast_message = state_data.get('broadcast_message')
        
        if not broadcast_message:
            await callback.answer("❌ لم يتم العثور على الرسالة", show_alert=True)
            return
        
        language = user_data.get('preferred_language', 'en')
        
        # الحصول على جميع المستخدمين
        all_users = await user_service.get_all_users(active_only=True)
        
        sent_count = 0
        total_count = len(all_users)
        
        # إرسال الرسالة لجميع المستخدمين
        for user in all_users:
            try:
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=broadcast_message
                )
                sent_count += 1
                
                # تأخير قصير لتجنب حدود التلجرام
                await asyncio.sleep(0.1)
                
            except Exception as send_error:
                logger.warning(f"Failed to send broadcast to user {user.telegram_id}: {send_error}")
                continue
        
        # إرسال تقرير النتائج
        result_text = translator.get_text(
            'broadcast_sent',
            language,
            sent_count=sent_count,
            total_count=total_count
        )
        
        await callback.message.edit_text(result_text)
        await state.clear()
        await callback.answer("تم إرسال البث!" if language == "ar" else "Broadcast sent!")
        
    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        await callback.answer("❌ فشل في إرسال البث", show_alert=True)


# دالة تهيئة المعالجات
def setup_handlers(dp, bot_instance):
    """تهيئة جميع المعالجات"""
    
    # إعداد المجدول
    bot_scheduler.bot = bot_instance
    
    # تسجيل الموجهات
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(payment_router)
    
    logger.info("All handlers registered successfully")


# معالج الأخطاء العامة
async def error_handler(update, exception):
    """معالج الأخطاء العامة"""
    logger.error(f"Update {update} caused error {exception}")
    return True