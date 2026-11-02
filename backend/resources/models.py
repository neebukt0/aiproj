from django.db import models


class Resource(models.Model):
    class ResourceType(models.TextChoices):
        HALL = 'hall', 'Зал'
        PRIVATE_ROOM = 'private_room', 'Переговорная'
        OUTDOOR = 'outdoor', 'Открытая площадка'

    name = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices, default=ResourceType.PRIVATE_ROOM)
    capacity = models.PositiveIntegerField(default=1)
    image = models.ImageField(upload_to='resources/', null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name
