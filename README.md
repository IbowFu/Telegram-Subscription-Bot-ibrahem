بوت تلجرام للاشتراكات - Telegram Subscription Bot
بوت تلجرام احترافي لإدارة الاشتراكات في القنوات مع دعم كامل للغتين العربية والإنجليزية.

A professional Telegram bot for managing channel subscriptions with full Arabic and English support.

المميزات الرئيسية / Key Features
🌟 للمستخدمين / For Users
اشتراك مجاني: انضمام للقنوات العامة بدون رسوم
اشتراكات مدفوعة: خطط متعددة (أسبوعي، شهري، سنوي)
دفع آمن: دعم Stripe و PayPal
تنبيهات ذكية: تذكير قبل انتهاء الاشتراك بـ 24 ساعة
واجهة ثنائية اللغة: عربي وإنجليزي بالكامل
🔧 للمديرين / For Administrators
لوحة تحكم شاملة: إدارة كاملة عبر البوت
إحصائيات مفصلة: تتبع المستخدمين والإيرادات
إدارة الخطط: إضافة وتعديل خطط الاشتراك
البث الجماعي: إرسال رسائل لجميع المستخدمين
تقارير تلقائية: تقارير يومية وأسبوعية
🛡️ الأمان / Security
روابط آمنة: روابط دعوة لاستخدام واحد فقط
تشفير البيانات: حماية معلومات الدفع والمستخدمين
طرد تلقائي: إزالة المستخدمين عند انتهاء الاشتراك
متطلبات التشغيل / Requirements
Python 3.11+
PostgreSQL 13+ أو SQLite
Redis 6+ (اختياري)
حساب Stripe و/أو PayPal
التثبيت السريع / Quick Installation
1. استنساخ المشروع / Clone Repository
git clone <repository-url>
cd telegram_bot
2. إنشاء بيئة افتراضية / Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو / or
venv\Scripts\activate  # Windows
3. تثبيت المتطلبات / Install Dependencies
pip install -r requirements.txt
4. إعداد متغيرات البيئة / Setup Environment Variables
cp .env.example .env
# قم بتعديل ملف .env بالقيم الصحيحة
# Edit .env file with correct values
5. تهيئة قاعدة البيانات / Initialize Database
python -c "import asyncio; from database import init_database; asyncio.run(init_database())"
6. تشغيل البوت / Run Bot
python main.py
إعدادات مطلوبة / Required Configuration
متغيرات البيئة الأساسية / Essential Environment Variables
# رمز البوت من BotFather
BOT_TOKEN=your_bot_token_here

# إعدادات Stripe
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# إعدادات PayPal
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret

# معرفات القنوات
PUBLIC_CHANNEL_ID=-1001234567890
PRIVATE_CHANNEL_ID=-1001234567891

# معرفات المديرين
ADMIN_USER_IDS=123456789,987654321
هيكل المشروع / Project Structure
telegram_bot/
├── main.py              # الملف الرئيسي
├── config.py            # إعدادات التطبيق
├── database.py          # قاعدة البيانات والنماذج
├── handlers.py          # معالجات الرسائل
├── keyboards.py         # الأزرار التفاعلية
├── localization.py      # نظام الترجمة
├── payments.py          # نظام الدفع
├── scheduler.py         # المهام المجدولة
├── requirements.txt     # متطلبات Python
├── .env.example        # مثال متغيرات البيئة
└── README.md           # هذا الملف
الاستخدام / Usage
للمستخدمين العاديين / For Regular Users
البداية: أرسل /start للبوت
اختيار اللغة: اختر العربية أو الإنجليزية
تصفح الخطط: استعرض خطط الاشتراك المتاحة
الدفع: اختر طريقة الدفع وأكمل العملية
الانضمام: استخدم رابط الدعوة للانضمام للقناة
للمديرين / For Administrators
لوحة التحكم: اضغط على “لوحة التحكم” في القائمة الرئيسية
الإحصائيات: عرض إحصائيات المستخدمين والإيرادات
إدارة الخطط: إضافة أو تعديل خطط الاشتراك
البث الجماعي: إرسال رسائل لجميع المستخدمين
إدارة القنوات: إضافة أو تعديل القنوات
الميزات المتقدمة / Advanced Features
نظام الجدولة / Scheduling System
تنبيهات تلقائية قبل انتهاء الاشتراك
طرد تلقائي عند انتهاء الاشتراك
تقارير دورية للمديرين
تنظيف البيانات المؤقتة
نظام الدفع / Payment System
دعم Stripe و PayPal
معالجة آمنة للمدفوعات
webhooks للتحديثات الفورية
إدارة المبالغ المستردة
الأمان / Security
تشفير البيانات الحساسة
روابط دعوة آمنة
التحقق من صحة المدفوعات
حماية من إعادة الاستخدام
استكشاف الأخطاء / Troubleshooting
مشاكل شائعة / Common Issues
خطأ في رمز البوت

خطأ: Invalid bot token
الحل: تأكد من صحة BOT_TOKEN في ملف .env
فشل الاتصال بقاعدة البيانات

خطأ: Database connection failed
الحل: تأكد من صحة DATABASE_URL وأن قاعدة البيانات تعمل
فشل في إعداد Webhook

خطأ: Webhook setup failed
الحل: تأكد من صحة WEBHOOK_HOST و WEBHOOK_PORT
سجلات الأخطاء / Error Logs
يتم حفظ سجلات الأخطاء في ملف bot.log. لعرض السجلات:

tail -f bot.log
التطوير / Development
إضافة ميزة جديدة / Adding New Features
إنشاء معالج جديد في handlers.py
إضافة الترجمات في localization.py
إنشاء أزرار في keyboards.py
تحديث قاعدة البيانات إذا لزم الأمر
اختبار البوت / Testing
# تشغيل الاختبارات
python -m pytest tests/

# تشغيل البوت في وضع التطوير
DEBUG=true python main.py
النشر / Deployment
استخدام Docker / Using Docker
# بناء الصورة
docker build -t telegram-bot .

# تشغيل الحاوية
docker run -d --env-file .env telegram-bot
النشر على الخادم / Server Deployment
رفع الملفات للخادم
تثبيت المتطلبات
إعداد متغيرات البيئة
تشغيل البوت كخدمة
الدعم / Support
للحصول على المساعدة:

راجع هذا الدليل أولاً
تحقق من سجلات الأخطاء
تأكد من صحة الإعدادات
اتصل بفريق الدعم
الترخيص / License
هذا المشروع مرخص تحت رخصة MIT. راجع ملف LICENSE للتفاصيل.

This project is licensed under the MIT License. See LICENSE file for details.

المساهمة / Contributing
نرحب بالمساهمات! يرجى:

عمل Fork للمشروع
إنشاء فرع جديد للميزة
إجراء التغييرات
إرسال Pull Request
We welcome contributions! Please:

Fork the project
Create a feature branch
Make your changes
Submit a Pull Request