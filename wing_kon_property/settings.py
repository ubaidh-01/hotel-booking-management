from pathlib import Path
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-%#l3qtlobp+0_hq8=(#h*v^ws=%b@gdam*y!4)_(bzp1aseieg'

DEBUG = True
env = environ.Env(
    DEBUG=(bool, False)
)

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

ALLOWED_HOSTS = ['ubaid001.pythonanywhere.com', '127.0.0.1']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Custom CRM Apps
    'properties',
    'tenants',
    'bookings',
    'contracts',
    'payments',
    'maintenance',
    'reports',
    # Celery & Notifications
    'django_celery_beat',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wing_kon_property.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wing_kon_property.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TIMEZONE = 'Asia/Hong_Kong'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'


# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'send-rent-reminders': {
        'task': 'notifications.tasks.send_rent_reminders',
        'schedule': 86400.0,  # Every 24 hours
    },
    'send-contract-reminders': {
        'task': 'notifications.tasks.send_contract_reminders',
        'schedule': 86400.0,  # Every 24 hours
    },
    'send-move-out-reminders': {
        'task': 'notifications.tasks.send_move_out_reminders',
        'schedule': 86400.0,  # Every 24 hours
    },

    'send-final-move-out-warnings': {
        'task': 'notifications.tasks.send_final_move_out_warnings',
        'schedule': 86400.0,  # Every 24 hours
    },
    'send-birthday-wishes': {
        'task': 'notifications.tasks.send_birthday_wishes',
        'schedule': 86400.0,  # Every 24 hours
    },
    'process-late-fees': {
        'task': 'notifications.tasks.process_late_fees',
        'schedule': 86400.0,  # Every 24 hours
    },
    'sync-room-status': {
        'task': 'notifications.tasks.sync_room_status',
        'schedule': 86400.0,  # Every 24 hours
    },
    'detect-rent-increases': {
            'task': 'notifications.tasks.detect_rent_increases',
            'schedule': 86400.0,  # Every 24 hours
        },

    'create-late-fee-payments': {
        'task': 'notifications.tasks.create_late_fee_payments',
        'schedule': 86400.0,  # Every 24 hours
    },
    'allocate-utility-bills': {
        'task': 'notifications.tasks.allocate_utility_bills',
        'schedule': 86400.0,  # Every 24 hours
    },

    'send-utility-reminders': {
        'task': 'notifications.tasks.send_utility_payment_reminders',
        'schedule': 86400.0,  # Every 24 hours
    },
    'check-maintenance-overdue': {
        'task': 'notifications.tasks.check_maintenance_overdue',
        'schedule': 86400.0,  # Every 24 hours
    },

    'send-maintenance-updates': {
        'task': 'notifications.tasks.send_maintenance_updates_to_tenants',
        'schedule': 86400.0,  # Every 24 hours
    },

    'escalate-high-priority-tickets': {
        'task': 'notifications.tasks.escalate_high_priority_tickets',
        'schedule': 86400.0,  # Every 24 hours
    },

    'generate-payment-receipts': {
        'task': 'notifications.tasks.generate_payment_receipts',
        'schedule': 3600.0,  # Every hour
    },

    'process-pending-receipts': {
        'task': 'notifications.tasks.process_pending_receipts',
        'schedule': 1800.0,  # Every 30 minutes
    },

}
# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


JAZZMIN_SETTINGS = {
    "site_title": "Wing Kong Property Admin",
    "site_header": "Wing Kong Property",
    "site_brand": "Wing Kong",
    "welcome_sign": "Welcome to Wing Kong Admin",
    "copyright": "Wing Kong © 2025",
    "show_ui_builder": True,  # Enables a live UI style editor in the admin

    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
    },
    "hide_models": [
        "auth.Group",
        "django_celery_beat.PeriodicTask",
        "django_celery_beat.IntervalSchedule",
        "django_celery_beat.CrontabSchedule",
        "django_celery_beat.SolarSchedule",
        "django_celery_beat.ClockedSchedule",
    ],
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# ✅ Add this for deployment on PythonAnywhere
STATIC_ROOT = '/home/ubaid001/hotel-booking-management/staticfiles'


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


EMAIL_BACKEND = env('EMAIL_BACKEND')
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
TO_EMAIL = env('TO_EMAIL')

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/reports/'
