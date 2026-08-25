from app.models.member import Member
from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository[Member]):
    model = Member
