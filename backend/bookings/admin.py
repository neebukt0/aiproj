from django.contrib import admin
from django.db import models
from django.utils import timezone

from bookings.models import Booking


class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'resource', 'status', 'start_at', 'end_at', 'held_until', 'created_at')
    list_filter = ('status', 'resource')
    ordering = ('-id',)


admin.site.register(Booking, BookingAdmin)
