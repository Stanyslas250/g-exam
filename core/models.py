from django.db import models
from simple_history.models import HistoricalRecords
import uuid



class BaseModel(models.Model):
  """
    Modèle de base à hériter pour tous les modèles de l'application.
    Contient les éléments communs (UUID, timestamps, historique, etc.) à tous les modèles.
  """
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
  updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
  history = HistoricalRecords(inherit=True)

  class Meta:
    abstract = True

  def __str__(self):
    return f"{self.id}"