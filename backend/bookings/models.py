from django.db import models


class BookingStatus(models.TextChoices):
    CREATED = 'created', 'Создана'
    CONFIRMED = 'confirmed', 'Подтверждена'
    COMPLETED = 'completed', 'Завершена'
    CANCELLED = 'cancelled', 'Отменена'


class Booking(models.Model):
    HOLD_MINUTES = 10

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='bookings'
    )
    resource = models.ForeignKey(
        'resources.Resource', on_delete=models.CASCADE, related_name='bookings'
    )
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.CREATED)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    held_until = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_bookings'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'Booking #{self.id} ({self.status})'
