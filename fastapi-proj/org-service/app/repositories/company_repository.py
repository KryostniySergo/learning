from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Репозиторий для работы с компаниями."""

    model = Company
