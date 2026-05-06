"""
LexAI — Base Model with UUID primary key, timestamps, and soft delete.
All domain models inherit from this.
"""
import uuid

from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """Default manager that filters out soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """Manager that includes soft-deleted records."""
    pass


class BaseModel(models.Model):
    """
    Abstract base model for all LexAI domain models.

    Features:
    - UUID primary key (no sequential ID leakage)
    - Automatic timestamps
    - Soft delete with deleted_at field
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Default manager filters out soft-deleted records
    objects = SoftDeleteManager()
    # Use all_objects to include soft-deleted records
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def delete(self, using=None, keep_parents=False):
        """Soft delete — sets deleted_at timestamp."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete from database."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
